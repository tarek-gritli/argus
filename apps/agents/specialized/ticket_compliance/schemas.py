# apps/agents/specialized/ticket_compliance/schemas.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentInput:
    diff: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    installation_id: int = 0
    pr_title: str = ""
    pr_description: str = ""
