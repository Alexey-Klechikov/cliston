import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass
from datetime import date

from agents import CLISTON_CONFIG, MTB_CONFIG
from services.logging.operators import log_task_input, rename_log_file

from cliston.api.task.crew import build_crew
from cliston.api.task.models import CrewResponse


@dataclass
class TaskExecutionResult:
    task_id: str
    status: str
    response: str | None = None
    error: str | None = None


_task_results: dict[str, TaskExecutionResult] = {}


_CREW_KICKOFF_TIMEOUT_SECONDS = 300


def _contains_prompt_injection_junk(text: str) -> bool:
    lowered = text.lower()
    strong_markers = [
        '"action":',
        '"action_input":',
        "action input:",
        "using tool:",
        "```json",
    ]
    if any(marker in lowered for marker in strong_markers):
        return True

    junk_markers = [
        "### instruction",
        "## your task",
        "i'm sorry, but i'm sorry",
        "thought:",
        "action:",
        "action input:",
    ]
    marker_count = sum(1 for marker in junk_markers if marker in lowered)
    return marker_count >= 2


def _build_safe_generic_reply(user_message: str) -> str:
    return (
        "Dear Sir/Madam, I could not verify reliable web evidence for "
        f"'{user_message}' at the moment. "
        "Would you like me to try again with a narrower phrasing?"
    )


def register_task(task_id: str) -> None:
    _task_results[task_id] = TaskExecutionResult(task_id=task_id, status="queued")


def get_task_result(task_id: str) -> TaskExecutionResult | None:
    return _task_results.get(task_id)


def _process_message_sync(user_message: str, task_id: str) -> CrewResponse:
    crew = build_crew(agents_configs=[MTB_CONFIG, CLISTON_CONFIG], task_id=task_id)
    executor: concurrent.futures.ThreadPoolExecutor | None = None

    try:
        inputs = {
            "topic": user_message,
            "current_date": str(date.today()),
            "search_budget": "3",
        }

        logging.info("Starting crew kickoff for: %s", user_message)

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(crew.kickoff, inputs=inputs)

        try:
            output = future.result(timeout=_CREW_KICKOFF_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            logging.error("Crew kickoff timed out")
            future.cancel()
            return CrewResponse(response=_build_safe_generic_reply(user_message))
        except Exception:
            logging.exception("Crew kickoff failed")
            return CrewResponse(response=_build_safe_generic_reply(user_message))

    finally:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    output_text = str(output)

    if _contains_prompt_injection_junk(output_text):
        return CrewResponse(response=_build_safe_generic_reply(user_message))

    logging.info("Crew finished successfully.")
    return CrewResponse(response=output_text)


async def process_message_background(user_message: str, task_id: str) -> None:
    task_state = _task_results.get(task_id)
    if task_state is None:
        register_task(task_id)
        task_state = _task_results[task_id]

    task_state.status = "running"

    log_task_input(user_message=user_message, task_id=task_id)

    try:
        result = await asyncio.to_thread(_process_message_sync, user_message, task_id)
        task_state.status = "completed"
        task_state.response = result.response
        task_state.error = None
        logging.info("Task %s completed. Result: %s", task_id, result.response)

    except Exception as exc:
        task_state.status = "failed"
        task_state.response = None
        task_state.error = str(exc)
        logging.exception("Task %s failed", task_id)

    rename_log_file(task_id=task_id, state=task_state.status)
