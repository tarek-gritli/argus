from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from integrations.notifications.dispatcher import dispatch_review_completed
from integrations.notifications.schemas import ReviewSummary


def _summary() -> ReviewSummary:
    return ReviewSummary(
        org_id="org-1",
        repo="acme/api",
        pr_number=42,
        pr_url="https://github.com/acme/api/pull/42",
        finding_count=3,
        critical_count=1,
        high_count=1,
    )


def _integration(kind: str, config: dict, enabled: bool = True) -> MagicMock:
    i = MagicMock()
    i.id = "int-1"
    i.kind = kind
    i.enabled = enabled
    i.config = config
    return i


def _session_with(integrations: list) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = integrations
    session.execute.return_value = result
    return session


@pytest.mark.asyncio
async def test_dispatches_to_slack():
    integration = _integration("slack", {"webhook_url": "https://hooks.slack.com/x"})
    session = _session_with([integration])
    with patch("integrations.notifications.dispatcher.post_to_slack") as mock_slack:
        await dispatch_review_completed(session, _summary())
        mock_slack.assert_called_once_with("https://hooks.slack.com/x", _summary())


@pytest.mark.asyncio
async def test_dispatches_to_notion():
    integration = _integration("notion", {"token": "secret", "database_id": "db-uuid"})
    session = _session_with([integration])
    with patch("integrations.notifications.dispatcher.append_to_notion_db") as mock_notion:
        await dispatch_review_completed(session, _summary())
        mock_notion.assert_called_once_with("secret", "db-uuid", _summary())


@pytest.mark.asyncio
async def test_skips_slack_when_no_webhook_url():
    integration = _integration("slack", {})
    session = _session_with([integration])
    with patch("integrations.notifications.dispatcher.post_to_slack") as mock_slack:
        await dispatch_review_completed(session, _summary())
        mock_slack.assert_not_called()


@pytest.mark.asyncio
async def test_swallows_error_and_continues():
    slack = _integration("slack", {"webhook_url": "https://hooks.slack.com/x"})
    notion = _integration("notion", {"token": "k", "database_id": "d"})
    session = _session_with([slack, notion])
    with (
        patch("integrations.notifications.dispatcher.post_to_slack", side_effect=RuntimeError("boom")),
        patch("integrations.notifications.dispatcher.append_to_notion_db") as mock_notion,
    ):
        await dispatch_review_completed(session, _summary())
        mock_notion.assert_called_once()


@pytest.mark.asyncio
async def test_no_integrations_does_nothing():
    session = _session_with([])
    with (
        patch("integrations.notifications.dispatcher.post_to_slack") as mock_slack,
        patch("integrations.notifications.dispatcher.append_to_notion_db") as mock_notion,
    ):
        await dispatch_review_completed(session, _summary())
        mock_slack.assert_not_called()
        mock_notion.assert_not_called()
