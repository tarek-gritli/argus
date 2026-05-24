from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReviewSummary:
    org_id: str
    repo: str
    pr_number: int
    pr_url: str
    finding_count: int
    critical_count: int
    high_count: int
