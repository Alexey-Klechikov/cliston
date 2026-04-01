from datetime import datetime

from pydantic import BaseModel, model_validator

from cliston.core.models import ToolCall

ERROR_MARKERS = (
    "error",
    "failure",
    "infrastructure error",
    "infiltration failure",
    "tactical failure",
    "timed out",
    "timeout",
)


class TacticalManual(BaseModel):
    domain: str
    objective: str
    manual: str
    success_count: int = 0
    failure_count: int = 0
    last_updated: datetime

    @model_validator(mode="after")
    def normalize_domain(self):
        self.domain = self.domain.lower().replace("www.", "").strip()
        return self

    @property
    def reliability(self) -> float:
        total_attempts = self.success_count + self.failure_count
        return self.success_count / total_attempts if total_attempts > 0 else 1.0


class ToolCallTrace(BaseModel):
    tool_call: ToolCall
    result: str

    @property
    def success(self) -> bool:
        return bool(self.result) and not any(marker in self.result.lower() for marker in ERROR_MARKERS)
