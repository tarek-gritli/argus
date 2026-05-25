"""Security agent internal schemas. Not part of shared contract."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class RepoConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    exempt_paths: list[str] = Field(default_factory=lambda: ["tests/", "fixtures/"])
    severity_overrides: dict[str, Severity] = Field(default_factory=dict)


class AgentTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diff: str
    pr_number: int
    repo_id: str
    repo_config: RepoConfig = Field(default_factory=RepoConfig)
    vector_context: list[str] = Field(default_factory=list)


class DiffLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    line: int
    content: str


class SecretHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    line: int
    matched_value: str
    pattern_name: str
    entropy: float | None = None
    severity_hint: Severity = Severity.HIGH


class SastHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    line: int
    rule_id: str
    owasp_id: str
    severity_hint: Severity


class DependencyHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: str
    version: str
    cve_id: str
    cvss_score: float
    fix_version: str | None = None
    severity_hint: Severity = Severity.MEDIUM


class ScannerHits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secrets: list[SecretHit] = Field(default_factory=list)
    sast: list[SastHit] = Field(default_factory=list)
    dependencies: list[DependencyHit] = Field(default_factory=list)


class SecurityContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_prompt: str
    owasp_rules: dict[str, Any]
    lang_rules: dict[str, Any]
    exempt_paths: list[str]
    severity_overrides: dict[str, Severity]


class RawFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    line: int
    category: str
    owasp_id: str
    severity: Severity
    exploit_path: str
    message: str
    suggested_fix: str
    confidence: float = Field(ge=0.0, le=1.0)


class ReflectionAction(str, Enum):
    KEEP = "KEEP"
    DROP = "DROP"
    DOWNGRADE = "DOWNGRADE"


class ReflectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_index: int
    action: ReflectionAction
    reason: str
    revised_severity: Severity | None = None


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str = "security"
    file: str
    line: int
    severity: Severity
    owasp_id: str
    category: str
    message: str
    suggested_fix: str
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    pr_number: int
    repo: str
    agent: str = "security"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    findings: list[Finding] = Field(default_factory=list)
