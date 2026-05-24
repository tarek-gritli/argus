from __future__ import annotations

from notion_client import Client

from .schemas import ReviewSummary


def append_to_notion_db(api_key: str, database_id: str, summary: ReviewSummary) -> None:
    client = Client(auth=api_key)
    client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Name": {"title": [{"text": {"content": f"{summary.repo} PR #{summary.pr_number}"}}]},
            "PR URL": {"url": summary.pr_url},
            "Findings": {"number": summary.finding_count},
            "Critical": {"number": summary.critical_count},
            "High": {"number": summary.high_count},
        },
    )
