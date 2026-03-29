from api.task.models import TaskResultResponse, TaskSubmitResponse
from fastapi import APIRouter, HTTPException, status

from cliston.api.task.models import TaskInput
from cliston.api.task.operators import handle_execute_task, handle_get_task

router = APIRouter(prefix="/task", tags=["CrewAI"])


@router.post("/execute", response_model=TaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_task(task_input: TaskInput) -> TaskSubmitResponse:
    task_state = await handle_execute_task(task_input.user_query)

    return TaskSubmitResponse(task_id=task_state.task_id, status="queued")


@router.get("/{task_id}", response_model=TaskResultResponse, status_code=status.HTTP_200_OK)
async def get_task(task_id: str) -> TaskResultResponse:
    task_state = handle_get_task(task_id)
    if task_state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return TaskResultResponse(
        task_id=task_state.task_id,
        status=task_state.status,
        response=task_state.response,
        error=task_state.error,
    )
