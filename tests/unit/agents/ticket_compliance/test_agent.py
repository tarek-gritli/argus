# tests/unit/agents/ticket_compliance/test_agent.py
from unittest.mock import MagicMock, patch

from specialized.ticket_compliance.agent import run_ticket_compliance_agent
from specialized.ticket_compliance.providers.base import TicketData
from specialized.ticket_compliance.schemas import AgentInput
from specialized.ticket_compliance.validator import validate_findings


def test_validate_drops_low_confidence():
    findings = [
        {"agent": "ticket_compliance", "severity": "high", "file": "a.py", "line_start": 1, "line_end": 1, "title": "Missing feature", "description": "x", "suggestion": "add it", "confidence": 0.85},
        {"agent": "ticket_compliance", "severity": "medium", "file": "b.py", "line_start": 1, "line_end": 1, "title": "Partial impl", "description": "y", "suggestion": "fix it", "confidence": 0.3},
    ]
    result = validate_findings(findings)
    assert len(result) == 1
    assert result[0]["title"] == "Missing feature"


def test_validate_keeps_empty_list():
    assert validate_findings([]) == []


def test_validate_keeps_exactly_at_floor():
    findings = [
        {"agent": "ticket_compliance", "severity": "low", "file": "a.py", "line_start": 1, "line_end": 1, "title": "Minor gap", "description": "z", "suggestion": "fix it", "confidence": 0.6},
    ]
    result = validate_findings(findings)
    assert len(result) == 1


def _make_input(**kwargs):
    defaults = dict(
        diff="--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1,1 +1,2 @@\n+def login(): pass",
        repo_full_name="org/repo",
        pr_number=10,
        head_sha="abc1234",
        base_sha="def5678",
        pr_title="Closes #42: add login endpoint",
        pr_description="Implements the login feature from issue #42.",
        installation_id=99,
    )
    defaults.update(kwargs)
    return AgentInput(**defaults)


def test_returns_empty_when_no_issue_refs():
    agent_input = _make_input(pr_title="chore: update deps", pr_description="")
    result = run_ticket_compliance_agent(agent_input, providers={})
    assert result == []


def test_returns_empty_when_provider_returns_none():
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = None
    agent_input = _make_input()
    result = run_ticket_compliance_agent(agent_input, providers={"github_issues": mock_provider})
    assert result == []


def test_llm_findings_converted_to_finding_schema():
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = TicketData(
        id="42",
        title="Add login endpoint",
        description="Create a POST /login endpoint that authenticates users.",
        url="https://github.com/org/repo/issues/42",
    )

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='[{"agent":"ticket_compliance","severity":"high","file":"src/auth.py","line_start":1,"line_end":1,"title":"Missing auth logic","description":"Login endpoint is empty.","suggestion":"Add auth check.","confidence":0.9}]')]

    with patch("specialized.ticket_compliance.agent.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        with patch("specialized.ticket_compliance.agent.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "test-key"
            result = run_ticket_compliance_agent(agent_input=_make_input(), providers={"github_issues": mock_provider})

    assert len(result) == 1
    assert result[0].agent == "ticket_compliance"
    assert result[0].severity == "high"
    assert result[0].confidence == 0.9


def test_low_confidence_findings_filtered_out():
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = TicketData(id="42", title="Add login", description="Add POST /login", url="https://github.com/org/repo/issues/42")

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='[{"agent":"ticket_compliance","severity":"low","file":"src/auth.py","line_start":1,"line_end":1,"title":"Minor gap","description":"Missing docstring.","suggestion":"Add docstring.","confidence":0.2}]')]

    with patch("specialized.ticket_compliance.agent.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        with patch("specialized.ticket_compliance.agent.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "test-key"
            result = run_ticket_compliance_agent(agent_input=_make_input(), providers={"github_issues": mock_provider})

    assert result == []


def test_analyze_adapter_returns_list():
    """Smoke test: analyze() returns a list (empty when no issue refs found)."""
    from specialized.ticket_compliance import analyze

    mock_file = MagicMock()
    mock_file.filename = "src/main.py"
    mock_file.patch = ""

    mock_payload = MagicMock()
    mock_payload.repo_full_name = "org/repo"
    mock_payload.pr_number = 1
    mock_payload.head_sha = "abc"
    mock_payload.base_sha = "def"
    mock_payload.installation_id = 0
    mock_payload.pr_title = ""
    mock_payload.pr_body = ""

    with patch("specialized.ticket_compliance.run_ticket_compliance_agent", return_value=[]):
        result = analyze([mock_file], "diff text", mock_payload)

    assert isinstance(result, list)
