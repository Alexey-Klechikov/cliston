from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

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
    steps: list[str] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    last_updated: datetime

    @staticmethod
    def normalize_steps(steps: list[str] | None) -> list[str]:
        if not steps:
            return []

        return [str(step).strip() for step in steps if str(step).strip()]

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


class ReportResult(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ReportManual(BaseModel):
    name: str
    steps: list[str]


class Report(BaseModel):
    result: ReportResult = ReportResult.FAILURE
    data: str | None = None
    summary: str | None = None
    manual: ReportManual | None = None

    @model_validator(mode="before")
    def validate_manual(cls, values):
        values["result"] = ReportResult[values.get("result", "FAILURE").upper()]
        return values
