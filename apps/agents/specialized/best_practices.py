from __future__ import annotations

from typing import Any

from integrations.github import PullRequestPayload
from shared.schemas import FindingSchema


def analyze(files: list[Any], diff: str, pr_payload: PullRequestPayload) -> list[FindingSchema]:
    return []
