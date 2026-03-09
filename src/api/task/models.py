from pydantic import BaseModel, Field


class TaskSubmitResponse(BaseModel):
    task_id: str = Field(..., description="Server-generated task identifier")
    status: str = Field(..., description="Submission status")
