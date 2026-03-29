from pydantic import BaseModel, Field


class TaskState(BaseModel):
    task_id: str
    status: str
    response: str | None = None
    error: str | None = None

    def fail(self, error_message: str):
        self.status = "failed"
        self.response = None
        self.error = error_message

    def complete(self, response: str):
        self.status = "completed"
        self.response = response
        self.error = None


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

    user_query: str = Field(..., min_length=1, description="The message from the user")


class CrewResponse(BaseModel):
    """Structured response returned by the crew."""

    response: str = Field(..., description="Raw text output from the crew")
