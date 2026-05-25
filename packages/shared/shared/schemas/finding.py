from typing import Literal

from pydantic import BaseModel

AgentType = Literal["security", "quality", "testing", "documentation", "ticket_compliance"]
SeverityType = Literal["critical", "high", "medium", "low", "info"]


class FixSchema(BaseModel):
    diff: str | None = None
    description: str | None = None


class FindingSchema(BaseModel):
    agent: AgentType
    severity: SeverityType
    file: str
    line_start: int
    line_end: int
    title: str
    description: str
    suggestion: str | None = None
    confidence: float  # 0.0-1.0
    fix: FixSchema | None = None
