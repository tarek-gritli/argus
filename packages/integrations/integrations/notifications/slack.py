from __future__ import annotations

import httpx

from .schemas import ReviewSummary


def _build_message(summary: ReviewSummary) -> str:
    return f"*Argus review complete* — `{summary.repo}` PR #{summary.pr_number}\n{summary.finding_count} findings ({summary.critical_count} critical, {summary.high_count} high)\n<{summary.pr_url}|View PR>"


def post_to_slack(webhook_url: str, summary: ReviewSummary) -> None:
    httpx.post(webhook_url, json={"text": _build_message(summary)}, timeout=10).raise_for_status()


def post_to_slack_token(token: str, channel: str, summary: ReviewSummary) -> None:
    resp = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"channel": channel, "text": _build_message(summary)},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise ValueError(f"Slack API error: {data.get('error')}")
