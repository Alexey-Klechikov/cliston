import asyncio
import logging
from dataclasses import dataclass

from services.logging.operators import log_task_input, rename_log_file

from cliston.core.cliston import call_cliston


@dataclass
class TaskExecutionResult:
    task_id: str
    status: str
    response: str | None = None
    error: str | None = None


_task_results: dict[str, TaskExecutionResult] = {}


def _build_safe_generic_reply(user_message: str) -> str:
    return (
        "Apologies, Sir. The investigation into "
        f"'{user_message}' hit a bureaucratic brick wall. "
        "Shall we try a different angle?"
    )


def _register_task(task_id: str) -> None:
    _task_results[task_id] = TaskExecutionResult(task_id=task_id, status="running")


def handle_get_task(task_id: str) -> TaskExecutionResult | None:
    return _task_results.get(task_id)


async def handle_execute_task(user_message: str, task_id: str) -> None:
    """
    Directly calls the Cliston Orchestrator.
    Cliston handles the delegation to MTB internally.
    """
    log_task_input(user_message=user_message, task_id=task_id)

    task_state = _task_results.get(task_id)
    if task_state is None:
        _register_task(task_id)
        task_state = _task_results[task_id]

    try:
        # Cliston will manage the multi-turn loop and MTB delegation.
        logging.info("Cliston taking the case: %s", user_message)

        # Adding a timeout at the top level for safety
        async with asyncio.timeout(300):
            result_text = await call_cliston(user_query=user_message, task_id=task_id)

        if not result_text:
            raise ValueError("Cliston returned an empty response.")

        task_state.status = "completed"
        task_state.response = result_text
        task_state.error = None
        logging.info("Task %s completed by Cliston.", task_id)

    except asyncio.TimeoutError:
        task_state.status = "failed"
        task_state.response = _build_safe_generic_reply(user_message)
        task_state.error = "Timed out."
        logging.error("Task %s timed out", task_id)

    except Exception as exc:
        task_state.status = "failed"
        task_state.response = _build_safe_generic_reply(user_message)
        task_state.error = str(exc)
        logging.exception("Task %s failed", task_id)

    finally:
        rename_log_file(task_id=task_id, state=task_state.status)
