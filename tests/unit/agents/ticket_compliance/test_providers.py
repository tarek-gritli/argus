# tests/unit/agents/ticket_compliance/test_providers.py
from unittest.mock import MagicMock

from specialized.ticket_compliance.providers.base import TicketData
from specialized.ticket_compliance.providers.github_issues import GitHubIssuesProvider
from specialized.ticket_compliance.schemas import AgentInput


def test_ticket_data_fields():
    td = TicketData(
        id="42",
        title="Add rate limiting to the API",
        description="We need per-org rate limiting on the gateway.",
        url="https://github.com/org/repo/issues/42",
    )
    assert td.id == "42"
    assert td.title == "Add rate limiting to the API"


def test_agent_input_defaults():
    inp = AgentInput(
        diff="",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="abc",
        base_sha="def",
        installation_id=0,
    )
    assert inp.pr_title == ""
    assert inp.pr_description == ""


def test_github_issues_provider_fetches_issue():
    mock_gh = MagicMock()
    mock_issue = MagicMock()
    mock_issue.title = "Add rate limiting"
    mock_issue.body = "We need per-org limits."
    mock_issue.html_url = "https://github.com/org/repo/issues/42"
    mock_gh.get_repo.return_value.get_issue.return_value = mock_issue

    provider = GitHubIssuesProvider(gh_client=mock_gh, repo_full_name="org/repo")
    result = provider.fetch("42")

    assert result is not None
    assert result.id == "42"
    assert result.title == "Add rate limiting"
    assert result.description == "We need per-org limits."


def test_github_issues_provider_returns_none_on_error():
    mock_gh = MagicMock()
    mock_gh.get_repo.side_effect = Exception("not found")

    provider = GitHubIssuesProvider(gh_client=mock_gh, repo_full_name="org/repo")
    result = provider.fetch("99")
    assert result is None


def test_github_issues_provider_handles_none_body():
    mock_gh = MagicMock()
    mock_issue = MagicMock()
    mock_issue.title = "Empty issue"
    mock_issue.body = None
    mock_issue.html_url = "https://github.com/org/repo/issues/5"
    mock_gh.get_repo.return_value.get_issue.return_value = mock_issue

    provider = GitHubIssuesProvider(gh_client=mock_gh, repo_full_name="org/repo")
    result = provider.fetch("5")

    assert result is not None
    assert result.description == ""
