from __future__ import annotations

import httpx

from .dispatcher import ReviewSummary


def post_to_slack(webhook_url: str, summary: ReviewSummary) -> None:
    text = f"*Argus review complete* — `{summary.repo}` PR #{summary.pr_number}\n{summary.finding_count} findings ({summary.critical_count} critical, {summary.high_count} high)\n<{summary.pr_url}|View PR>"
    httpx.post(webhook_url, json={"text": text}, timeout=10)
