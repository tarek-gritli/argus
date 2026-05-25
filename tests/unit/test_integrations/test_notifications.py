import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.notifications.notion import append_to_notion_db
from integrations.notifications.schemas import ReviewSummary
from integrations.notifications.slack import post_to_slack


def _summary() -> ReviewSummary:
    return ReviewSummary(
        org_id="org-1",
        repo="acme/api",
        pr_number=42,
        pr_url="https://github.com/acme/api/pull/42",
        finding_count=5,
        critical_count=1,
        high_count=2,
    )


class TestPostToSlack:
    def test_sends_post_to_webhook_url(self):
        mock_response = MagicMock()
        with patch("integrations.notifications.slack.httpx.post", return_value=mock_response) as mock_post:
            post_to_slack("https://hooks.slack.com/test", _summary())
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://hooks.slack.com/test"
            assert "text" in kwargs["json"]
            mock_response.raise_for_status.assert_called_once()

    def test_message_contains_repo_and_pr(self):
        with patch("integrations.notifications.slack.httpx.post") as mock_post:
            post_to_slack("https://hooks.slack.com/test", _summary())
            text = mock_post.call_args.kwargs["json"]["text"]
            assert "acme/api" in text
            assert "42" in text
            assert "5" in text


class TestAppendToNotionDb:
    def _run(self, coro):
        return asyncio.run(coro)

    def _mock_httpx(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        return mock_ctx, mock_client

    def test_creates_page_in_database(self):
        mock_ctx, mock_client = self._mock_httpx()
        with patch("integrations.notifications.notion.httpx.AsyncClient", return_value=mock_ctx):
            self._run(append_to_notion_db("secret_key", "db-uuid", _summary()))
        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["parent"] == {"database_id": "db-uuid"}

    def test_page_properties_include_findings(self):
        mock_ctx, mock_client = self._mock_httpx()
        with patch("integrations.notifications.notion.httpx.AsyncClient", return_value=mock_ctx):
            self._run(append_to_notion_db("secret_key", "db-uuid", _summary()))
        props = mock_client.post.call_args.kwargs["json"]["properties"]
        assert props["Findings"]["number"] == 5
        assert props["Critical"]["number"] == 1
        assert props["High"]["number"] == 2
