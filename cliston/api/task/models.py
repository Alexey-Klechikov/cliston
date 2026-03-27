from pydantic import BaseModel, Field


class TaskSubmitResponse(BaseModel):
    task_id: str = Field(..., description="Server-generated task identifier")
    status: str = Field(..., description="Submission status")


class TaskResultResponse(BaseModel):
    task_id: str = Field(..., description="Server-generated task identifier")
    status: str = Field(..., description="queued, running, completed, or failed")
    response: str | None = Field(default=None, description="Final response when completed")
    error: str | None = Field(default=None, description="Failure details when status is failed")


class TaskInput(BaseModel):
    """Input passed into a crew kickoff."""

    user_message: str = Field(..., min_length=1, description="The message from the user")


class CrewResponse(BaseModel):
    """Structured response returned by the crew."""

    response: str = Field(..., description="Raw text output from the crew")
