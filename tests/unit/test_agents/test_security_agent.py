"""
Unit tests for the security agent LLM integration.

The Anthropic client is mocked so these run without credentials.
The fallback path (no API key) is also covered.
"""

from unittest.mock import MagicMock, patch

from specialized.security.schemas import (
    AgentTask,
    RawFinding,
    ReflectionAction,
    ReflectionDecision,
    RepoConfig,
    Severity,
)
from specialized.security.validator import build_fallback_decisions, validate_findings

DIFF_WITH_SECRET = """\
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,3 +1,5 @@
+SECRET_KEY = "sk_live_ABC123DEF456GHI"
+
 def get_user(user_id):
-    return db.query(f"SELECT * FROM users WHERE id = {user_id}")
+    query = f"SELECT * FROM users WHERE id = {user_id}"
"""

DIFF_CLEAN = """\
--- a/src/utils.py
+++ b/src/utils.py
@@ -1,2 +1,4 @@
+def add(a, b):
+    return a + b
"""


def _make_task(diff: str) -> AgentTask:
    return AgentTask(
        diff=diff,
        pr_number=1,
        repo_id="owner/repo",
        repo_config=RepoConfig(exempt_paths=["tests/", "fixtures/"]),
    )


def _make_parsed_response(findings: list, model_cls):
    mock_response = MagicMock()
    mock_response.parsed_output = model_cls(findings=findings)
    return mock_response


def _make_reflection_response(decisions: list, model_cls):
    mock_response = MagicMock()
    mock_response.parsed_output = model_cls(decisions=decisions)
    return mock_response


# ---------------------------------------------------------------------------
# Fallback path (no API key)
# ---------------------------------------------------------------------------


def test_fallback_detects_secret_and_sast():
    """Without an API key, the agent returns rule-based findings."""
    task = _make_task(DIFF_WITH_SECRET)

    settings_mock = MagicMock()
    settings_mock.anthropic_api_key = None

    with patch("specialized.security.agent.get_settings", return_value=settings_mock):
        from specialized.security.agent import run_security_agent

        result = run_security_agent(task)

    categories = {f.category for f in result.findings}
    assert "Hardcoded Secret" in categories
    assert "Injection" in categories


def test_fallback_clean_diff_no_findings():
    """A clean diff produces zero findings even without an API key."""
    task = _make_task(DIFF_CLEAN)

    settings_mock = MagicMock()
    settings_mock.anthropic_api_key = None

    with patch("specialized.security.agent.get_settings", return_value=settings_mock):
        from specialized.security.agent import run_security_agent

        result = run_security_agent(task)

    assert result.findings == []


# ---------------------------------------------------------------------------
# LLM path (API key present, Anthropic client mocked)
# ---------------------------------------------------------------------------


def test_llm_path_uses_claude_response():
    """When API key is set, findings come from the mocked Claude response."""
    from specialized.security.agent import _GeneratedFindings, _ReflectionDecisions

    llm_finding = RawFinding(
        file="src/auth.py",
        line=1,
        category="Hardcoded Secret",
        owasp_id="A02:2021",
        severity=Severity.CRITICAL,
        exploit_path="Secret exposed in source.",
        message="Live Stripe key hardcoded.",
        suggested_fix="Move to environment variable.",
        confidence=0.97,
    )
    llm_decision = ReflectionDecision(
        finding_index=0,
        action=ReflectionAction.KEEP,
        reason="High confidence, confirmed secret pattern.",
    )

    gen_response = MagicMock()
    gen_response.parsed_output = _GeneratedFindings(findings=[llm_finding])

    ref_response = MagicMock()
    ref_response.parsed_output = _ReflectionDecisions(decisions=[llm_decision])

    mock_client = MagicMock()
    mock_client.messages.parse.side_effect = [gen_response, ref_response]

    task = _make_task(DIFF_WITH_SECRET)

    settings_mock = MagicMock()
    settings_mock.anthropic_api_key = "sk-test-key"
    settings_mock.anthropic_model = "claude-sonnet-4-6"

    with (
        patch("anthropic.Anthropic", return_value=mock_client),
        patch("specialized.security.agent.get_settings", return_value=settings_mock),
    ):
        from specialized.security.agent import run_security_agent

        result = run_security_agent(task)

    assert len(result.findings) == 1
    assert result.findings[0].category == "Hardcoded Secret"
    assert result.findings[0].severity == Severity.CRITICAL
    assert mock_client.messages.parse.call_count == 2


def test_llm_reflection_can_drop_finding():
    """LLM reflection that DROPs a finding removes it from the output."""
    from specialized.security.agent import _GeneratedFindings, _ReflectionDecisions

    llm_finding = RawFinding(
        file="src/auth.py",
        line=1,
        category="Injection",
        owasp_id="A03:2021",
        severity=Severity.HIGH,
        exploit_path="SQL format string.",
        message="Possible SQL injection.",
        suggested_fix="Use parameterized queries.",
        confidence=0.45,
    )
    drop_decision = ReflectionDecision(
        finding_index=0,
        action=ReflectionAction.DROP,
        reason="Low confidence, context makes injection unlikely.",
    )

    gen_response = MagicMock()
    gen_response.parsed = _GeneratedFindings(findings=[llm_finding])

    ref_response = MagicMock()
    ref_response.parsed = _ReflectionDecisions(decisions=[drop_decision])

    mock_client = MagicMock()
    mock_client.messages.parse.side_effect = [gen_response, ref_response]

    task = _make_task(DIFF_WITH_SECRET)

    settings_mock = MagicMock()
    settings_mock.anthropic_api_key = "sk-test-key"
    settings_mock.anthropic_model = "claude-sonnet-4-6"

    with (
        patch("anthropic.Anthropic", return_value=mock_client),
        patch("specialized.security.agent.get_settings", return_value=settings_mock),
    ):
        from specialized.security.agent import run_security_agent

        result = run_security_agent(task)

    assert result.findings == []


def test_llm_fallback_on_api_error():
    """If the Claude API call raises, agent falls back to rule-based findings."""
    mock_client = MagicMock()
    mock_client.messages.parse.side_effect = Exception("API timeout")

    task = _make_task(DIFF_WITH_SECRET)

    settings_mock = MagicMock()
    settings_mock.anthropic_api_key = "sk-test-key"
    settings_mock.anthropic_model = "claude-sonnet-4-6"

    with (
        patch("anthropic.Anthropic", return_value=mock_client),
        patch("specialized.security.agent.get_settings", return_value=settings_mock),
    ):
        from specialized.security.agent import run_security_agent

        result = run_security_agent(task)

    # Fallback should still detect the secret
    assert any(f.category == "Hardcoded Secret" for f in result.findings)


def test_security_validator_drops_low_confidence_findings():
    finding = MagicMock()
    finding.severity = Severity.HIGH
    finding.confidence = 0.4
    finding.message = "Possible issue"

    assert validate_findings([finding]) == []


def test_security_validator_downgrades_critical_low_confidence():
    finding = MagicMock()
    finding.severity = Severity.CRITICAL
    finding.confidence = 0.8
    finding.message = "Possible issue"

    result = validate_findings([finding])
    assert len(result) == 1
    assert result[0].severity == Severity.HIGH


def test_security_fallback_decisions_follow_confidence_policy():
    raw_findings = [
        RawFinding(
            file="src/auth.py",
            line=1,
            category="Injection",
            owasp_id="A03:2021",
            severity=Severity.CRITICAL,
            exploit_path="SQL injection.",
            message="SQL injection.",
            suggested_fix="Use parameterized queries.",
            confidence=0.8,
        ),
        RawFinding(
            file="src/auth.py",
            line=2,
            category="Injection",
            owasp_id="A03:2021",
            severity=Severity.HIGH,
            exploit_path="SQL injection.",
            message="SQL injection.",
            suggested_fix="Use parameterized queries.",
            confidence=0.4,
        ),
    ]

    decisions = build_fallback_decisions(raw_findings)
    assert decisions[0].action == ReflectionAction.DOWNGRADE
    assert decisions[0].revised_severity == Severity.HIGH
    assert decisions[1].action == ReflectionAction.DROP
