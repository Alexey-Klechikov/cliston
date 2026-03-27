import asyncio
from uuid import uuid4

from api.task.models import TaskResultResponse, TaskSubmitResponse
from fastapi import APIRouter, HTTPException, status
from services.crewai.models import TaskInput
from services.crewai.operators import get_task_result, process_message_background, register_task

router = APIRouter(prefix="/task", tags=["CrewAI"])


@router.post("/execute", response_model=TaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_task(task_input: TaskInput) -> TaskSubmitResponse:
    task_id = str(uuid4())
    register_task(task_id)
    asyncio.create_task(process_message_background(task_input.user_message, task_id))
    return TaskSubmitResponse(task_id=task_id, status="queued")


@router.get("/{task_id}", response_model=TaskResultResponse, status_code=status.HTTP_200_OK)
async def get_task(task_id: str) -> TaskResultResponse:
    task_result = get_task_result(task_id)
    if task_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return TaskResultResponse(
        task_id=task_result.task_id,
        status=task_result.status,
        response=task_result.response,
        error=task_result.error,
    )
