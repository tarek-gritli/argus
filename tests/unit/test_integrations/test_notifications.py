from unittest.mock import MagicMock, patch

from integrations.notifications.dispatcher import ReviewSummary
from integrations.notifications.notion import append_to_notion_db
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
        with patch("integrations.notifications.slack.httpx.post") as mock_post:
            post_to_slack("https://hooks.slack.com/test", _summary())
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://hooks.slack.com/test"
            assert "text" in kwargs["json"]

    def test_message_contains_repo_and_pr(self):
        with patch("integrations.notifications.slack.httpx.post") as mock_post:
            post_to_slack("https://hooks.slack.com/test", _summary())
            text = mock_post.call_args.kwargs["json"]["text"]
            assert "acme/api" in text
            assert "42" in text
            assert "5" in text


class TestAppendToNotionDb:
    def test_creates_page_in_database(self):
        mock_client = MagicMock()
        with patch("integrations.notifications.notion.Client", return_value=mock_client):
            append_to_notion_db("secret_key", "db-uuid", _summary())
            mock_client.pages.create.assert_called_once()
            call_kwargs = mock_client.pages.create.call_args.kwargs
            assert call_kwargs["parent"] == {"database_id": "db-uuid"}

    def test_page_properties_include_findings(self):
        mock_client = MagicMock()
        with patch("integrations.notifications.notion.Client", return_value=mock_client):
            append_to_notion_db("secret_key", "db-uuid", _summary())
            props = mock_client.pages.create.call_args.kwargs["properties"]
            assert props["Findings"]["number"] == 5
            assert props["Critical"]["number"] == 1
            assert props["High"]["number"] == 2
