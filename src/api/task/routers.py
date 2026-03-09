import asyncio
from uuid import uuid4

from fastapi import APIRouter, status

from api.task.models import TaskSubmitResponse
from services.crewai.models import TaskInput
from services.crewai.operators import process_message_background

router = APIRouter(prefix="/task", tags=["CrewAI"])


@router.post("/execute", response_model=TaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_task(task_input: TaskInput) -> TaskSubmitResponse:
    task_id = str(uuid4())
    asyncio.create_task(process_message_background(task_input.user_message, task_id))
    return TaskSubmitResponse(task_id=task_id, status="queued")
