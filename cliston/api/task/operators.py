import asyncio
import logging
from uuid import uuid4

from api.task.models import TaskState
from core.cliston.agent import call_cliston
from services.logging.operators import log_task_input, rename_log_file

_task_states: dict[str, TaskState] = {}


def _build_safe_generic_reply(user_query: str) -> str:
    return (
        "Apologies, Sir. The investigation into "
        f"'{user_query}' hit a bureaucratic brick wall. "
        "Shall we try a different angle?"
    )


def handle_get_task(task_id: str) -> TaskState | None:
    return _task_states.get(task_id)


async def handle_execute_task(user_query: str) -> TaskState:
    """
    Directly calls the Cliston Orchestrator.
    Cliston handles the delegation to MTB internally.
    """
    task_state = TaskState(task_id=str(uuid4()), status="running")
    _task_states[task_state.task_id] = task_state

    log_task_input(user_query=user_query, task_id=task_state.task_id)

    # Cliston will manage the multi-turn loop and MTB delegation.
    logging.info("Cliston taking the case: %s", user_query)

    try:
        result_text = await call_cliston(user_query=user_query, task_id=task_state.task_id)
        if not result_text:
            raise ValueError("Cliston returned an empty response.")

        task_state.complete(result_text)
        logging.info("Task %s completed by Cliston.", task_state.task_id)

    except asyncio.TimeoutError:
        task_state.fail("Timed out")
        logging.error("Task %s timed out", task_state.task_id)

    except Exception as exc:
        task_state.fail(error_message=str(exc))
        logging.exception("Task %s failed", task_state.task_id)

    finally:
        rename_log_file(task_id=task_state.task_id, state=task_state.status)

    return task_state
