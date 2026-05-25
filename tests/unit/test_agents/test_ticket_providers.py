from unittest.mock import patch

from specialized.ticket_compliance.extractor import extract_ticket_refs
from specialized.ticket_compliance.providers.jira import JiraProvider
from specialized.ticket_compliance.providers.linear import LinearProvider
from specialized.ticket_compliance.providers.notion_ticket import NotionTicketProvider

# ─── Extractor ───────────────────────────────────────────────────────────────


class TestExtractor:
    def test_github_issue(self):
        refs = extract_ticket_refs("Fixes #42", "")
        assert ("github_issues", "42") in refs

    def test_jira_issue(self):
        refs = extract_ticket_refs("Implements PROJ-123", "")
        assert ("jira", "PROJ-123") in refs

    def test_linear_url(self):
        refs = extract_ticket_refs("", "https://linear.app/myteam/issue/ENG-99 is done")
        assert ("linear", "ENG-99") in refs

    def test_notion_url(self):
        refs = extract_ticket_refs("", "https://www.notion.so/My-Page-0123456789abcdef0123456789abcdef")
        assert ("notion", "0123456789abcdef0123456789abcdef") in refs

    def test_deduplication(self):
        refs = extract_ticket_refs("PROJ-1 PROJ-1", "PROJ-1")
        assert refs.count(("jira", "PROJ-1")) == 1

    def test_multiple_providers_in_one_pr(self):
        body = "Fixes #5\nPROJ-10\nhttps://linear.app/t/issue/ABC-1"
        refs = extract_ticket_refs("", body)
        providers = [r[0] for r in refs]
        assert "github_issues" in providers
        assert "jira" in providers
        assert "linear" in providers

    def test_no_refs_returns_empty(self):
        assert extract_ticket_refs("Add README", "No references here.") == []


# ─── JiraProvider ─────────────────────────────────────────────────────────────


class TestJiraProvider:
    def _provider(self):
        return JiraProvider("https://myorg.atlassian.net", "user@example.com", "token")

    def test_fetch_returns_ticket_data(self):
        with patch(
            "specialized.ticket_compliance.providers.jira.fetch_issue",
            return_value={"fields": {"summary": "Fix login bug", "description": "Details here"}},
        ):
            result = self._provider().fetch("PROJ-1")
        assert result is not None
        assert result.title == "Fix login bug"
        assert result.url == "https://myorg.atlassian.net/browse/PROJ-1"

    def test_fetch_returns_none_on_error(self):
        with patch("specialized.ticket_compliance.providers.jira.fetch_issue", side_effect=Exception("timeout")):
            result = self._provider().fetch("PROJ-1")
        assert result is None


# ─── LinearProvider ───────────────────────────────────────────────────────────


class TestLinearProvider:
    def _provider(self):
        return LinearProvider("lin_api_test123")

    def test_fetch_returns_ticket_data(self):
        with patch(
            "specialized.ticket_compliance.providers.linear.fetch_issue",
            return_value={"identifier": "ENG-5", "title": "Build widget", "description": "Details", "url": "https://linear.app/t/issue/ENG-5"},
        ):
            result = self._provider().fetch("ENG-5")
        assert result is not None
        assert result.title == "Build widget"

    def test_fetch_returns_none_when_issue_not_in_response(self):
        with patch("specialized.ticket_compliance.providers.linear.fetch_issue", return_value=None):
            result = self._provider().fetch("ENG-99")
        assert result is None

    def test_fetch_returns_none_on_error(self):
        with patch("specialized.ticket_compliance.providers.linear.fetch_issue", side_effect=Exception("timeout")):
            result = self._provider().fetch("ENG-1")
        assert result is None


# ─── NotionTicketProvider ─────────────────────────────────────────────────────


class TestNotionTicketProvider:
    def test_fetch_returns_ticket_data(self):
        with patch(
            "specialized.ticket_compliance.providers.notion_ticket.fetch_page",
            return_value={
                "properties": {"Name": {"type": "title", "title": [{"plain_text": "My Task"}]}},
                "url": "https://www.notion.so/My-Task-abc123",
            },
        ):
            result = NotionTicketProvider("secret_key").fetch("abc123")
        assert result is not None
        assert result.title == "My Task"
        assert result.url == "https://www.notion.so/My-Task-abc123"

    def test_fetch_returns_none_on_error(self):
        with patch("specialized.ticket_compliance.providers.notion_ticket.fetch_page", side_effect=Exception("API error")):
            result = NotionTicketProvider("secret_key").fetch("abc123")
        assert result is None
