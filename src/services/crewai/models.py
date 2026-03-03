from pydantic import BaseModel, Field


class TaskInput(BaseModel):
    """Input passed into a crew kickoff."""

    user_message: str = Field(..., min_length=1, description="The message from the user")


class CrewResponse(BaseModel):
    """Structured response returned by the crew."""

    response: str = Field(..., description="Raw text output from the crew")
