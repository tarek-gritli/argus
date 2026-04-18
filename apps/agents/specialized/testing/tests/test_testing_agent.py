"""
Tests for the testing agent.

Run with:
    uv run pytest tests/unit/agents/testing/ -v
"""

from __future__ import annotations

import os

import anthropic
import pytest

from ..schemas import AgentInput
from ..tools.coverage_analyzer import analyze_file, run_coverage_analysis
from ..tools.test_patterns import scan_test_patterns
from ..validator import validate_findings

# ---------------------------------------------------------------------------
# Coverage analyzer tests
# ---------------------------------------------------------------------------


class TestCoverageAnalyzer:
    def test_detects_public_functions_in_source(self):
        source = """\
def process_payment(amount, user_id):
    pass

def _internal_helper():
    pass

class PaymentService:
    def charge(self, amount):
        pass
"""
        metrics = analyze_file("src/payments.py", source)
        assert not metrics.is_test_file
        names = [s.name for s in metrics.public_symbols]
        assert "process_payment" in names
        assert "PaymentService" in names
        assert "charge" in names
        # Private helper should still be collected (agent filters it later)
        assert "_internal_helper" in names

    def test_skips_dunder_methods(self):
        source = """\
class Foo:
    def __init__(self):
        pass
    def __repr__(self):
        return "Foo"
    def public_method(self):
        pass
"""
        metrics = analyze_file("src/foo.py", source)
        names = [s.name for s in metrics.public_symbols]
        assert "__init__" not in names
        assert "__repr__" not in names
        assert "public_method" in names

    def test_identifies_test_file_by_prefix(self):
        metrics = analyze_file("tests/test_payments.py", "def test_charge(): pass")
        assert metrics.is_test_file

    def test_identifies_test_file_by_suffix(self):
        metrics = analyze_file("tests/payments_test.py", "def test_charge(): pass")
        assert metrics.is_test_file

    def test_counts_assertions_in_test(self):
        source = """\
def test_charge():
    result = charge(100)
    assert result.success
    assert result.amount == 100
    assertEqual(result.currency, "USD")
"""
        metrics = analyze_file("tests/test_payments.py", source)
        assert metrics.is_test_file
        assert len(metrics.test_functions) == 1
        fn = metrics.test_functions[0]
        assert fn.assertion_count >= 2

    def test_detects_zero_assertions(self):
        source = """\
def test_does_nothing():
    result = process(1)
    x = result + 1
"""
        metrics = analyze_file("tests/test_foo.py", source)
        assert metrics.test_functions[0].assertion_count == 0

    def test_detects_parametrize(self):
        source = """\
import pytest

@pytest.mark.parametrize("x,y", [(1,2),(3,4)])
def test_add(x, y):
    assert x + y > 0
"""
        metrics = analyze_file("tests/test_math.py", source)
        assert metrics.has_parametrize

    def test_detects_fixtures(self):
        source = """\
import pytest

@pytest.fixture
def client():
    return TestClient()

def test_endpoint(client):
    assert client.get("/").status_code == 200
"""
        metrics = analyze_file("tests/test_api.py", source)
        assert metrics.has_fixtures

    def test_non_python_file_skipped(self):
        result = run_coverage_analysis({"schema.json": "{}", "README.md": "# hello"})
        assert result.files == []

    def test_parse_error_handled_gracefully(self):
        metrics = analyze_file("src/broken.py", "def broken(:\n    pass")
        assert metrics.parse_error is not None

    def test_untested_symbols_detects_gap(self):
        source_files = {
            "src/service.py": "def process_payment(amount): pass",
        }
        result = run_coverage_analysis(source_files)
        untested = result.untested_symbols
        # No test file in diff → everything is untested
        assert any(s.name == "process_payment" for s, _ in untested)

    def test_untested_symbols_clears_when_referenced(self):
        files = {
            "src/service.py": "def process_payment(amount): pass",
            "tests/test_service.py": """\
def test_process_payment():
    result = process_payment(100)
    assert result is not None
""",
        }
        result = run_coverage_analysis(files)
        untested = result.untested_symbols
        # process_payment is referenced in the test body
        assert not any(s.name == "process_payment" for s, _ in untested)

    def test_prompt_context_warns_no_test_files(self):
        result = run_coverage_analysis({"src/foo.py": "def foo(): pass"})
        context = result.to_prompt_context()
        assert "NONE" in context or "no test files" in context.lower()

    def test_prompt_context_includes_symbol_names(self):
        result = run_coverage_analysis(
            {"src/foo.py": "def my_function(): pass\ndef another(): pass"}
        )
        context = result.to_prompt_context()
        assert "my_function" in context


# ---------------------------------------------------------------------------
# Test pattern scanner tests
# ---------------------------------------------------------------------------


class TestPatternScanner:
    def test_detects_trivially_true_assertion(self):
        diff = "@@ -1,1 +1,2 @@\n def test_x():\n+    assert True\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "trivially_true_assertion" in names

    def test_detects_weak_assertTrue_with_comparison(self):
        diff = "@@ -1,1 +1,2 @@\n def test_x():\n+    self.assertTrue(x == 5)\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "weak_assertTrue" in names

    def test_detects_sleep_in_test(self):
        diff = "@@ -1,1 +1,2 @@\n def test_x():\n+    time.sleep(1)\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "sleep_in_test" in names

    def test_detects_bare_except_in_test(self):
        diff = (
            "@@ -1,3 +1,5 @@\n def test_x():\n+    try:\n"
            "+        do_thing()\n+    except Exception:\n+        pass\n"
        )
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "bare_except_in_test" in names

    def test_detects_todo_in_test(self):
        diff = "@@ -1,2 +1,3 @@\n def test_x():\n+    # TODO: add real assertion\n+    pass\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "todo_in_test" in names

    def test_detects_test_without_assertion(self):
        diff = """\
@@ -1,4 +1,5 @@
+def test_process():
+    result = process(1)
+    x = result + 1
"""
        result = scan_test_patterns(diff, "tests/test_proc.py")
        names = [h.pattern_name for h in result.hits]
        assert "test_without_assertion" in names

    def test_no_false_positive_on_real_assertion(self):
        diff = """\
@@ -1,3 +1,4 @@
+def test_process():
+    result = process(1)
+    assert result == 42
"""
        result = scan_test_patterns(diff, "tests/test_proc.py")
        names = [h.pattern_name for h in result.hits]
        assert "test_without_assertion" not in names

    def test_no_false_positive_on_context_lines(self):
        diff = "@@ -1,2 +1,2 @@\n time.sleep(1)\n assert True\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        # These are context lines (no leading +), should not be flagged
        assert result.hits == []

    def test_prompt_context_renders_empty(self):
        result = scan_test_patterns("@@ -1 +1 @@\n unchanged\n", "tests/test_x.py")
        ctx = result.to_prompt_context()
        assert "no anti-patterns" in ctx


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestValidator:
    def _make_finding(self, **overrides) -> dict:
        base = {
            "agent": "testing",
            "severity": "high",
            "file": "src/service.py",
            "line_start": 10,
            "line_end": 30,
            "title": "process_payment has no test for negative amount",
            "description": "The function accepts negative amounts without raising an error.",
            "suggestion": (
                "Add test_process_payment_raises_on_negative_amount that calls "
                "process_payment(-1) and asserts ValueError is raised."
            ),
            "confidence": 0.9,
            "fix": None,
        }
        base.update(overrides)
        return base

    def test_valid_finding_passes(self):
        result = validate_findings([self._make_finding()])
        assert len(result) == 1

    def test_agent_field_forced(self):
        result = validate_findings([self._make_finding(agent="quality")])
        assert result[0]["agent"] == "testing"

    def test_low_confidence_dropped(self):
        result = validate_findings([self._make_finding(confidence=0.3)])
        assert result == []

    def test_missing_suggestion_dropped(self):
        result = validate_findings([self._make_finding(suggestion="")])
        assert result == []

    def test_invalid_line_range_dropped(self):
        result = validate_findings([self._make_finding(line_start=-1, line_end=0)])
        assert result == []

    def test_missing_required_field_dropped(self):
        bad = self._make_finding()
        del bad["description"]
        result = validate_findings([bad])
        assert result == []

    def test_speculative_finding_penalized_when_tests_exist(self):
        # "no test coverage" type claim with test files in diff → confidence penalized
        finding = self._make_finding(
            title="No test coverage for this module",
            description="There is no test coverage for this module",
            confidence=0.8,
        )
        result = validate_findings([finding], has_test_files_in_diff=True)
        if result:
            assert result[0]["confidence"] < 0.8

    def test_speculative_finding_not_penalized_without_test_files(self):
        finding = self._make_finding(
            title="No test coverage for this module",
            description="There is no test coverage for this module",
            confidence=0.8,
        )
        result = validate_findings([finding], has_test_files_in_diff=False)
        if result:
            assert result[0]["confidence"] == 0.8

    def test_sorted_by_severity(self):
        findings = [
            self._make_finding(severity="low", title="A"),
            self._make_finding(severity="critical", title="B"),
            self._make_finding(severity="high", title="C"),
        ]
        result = validate_findings(findings)
        severities = [f["severity"] for f in result]
        assert severities == ["critical", "high", "low"]

    def test_capped_at_max(self):
        findings = [self._make_finding(title=f"Issue {i}") for i in range(25)]
        result = validate_findings(findings)
        assert len(result) <= 12

    def test_severity_normalized(self):
        result = validate_findings([self._make_finding(severity="BLOCKER")])
        assert result[0]["severity"] == "medium"


# ---------------------------------------------------------------------------
# Integration smoke test (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY to call Claude",
)
def test_agent_end_to_end():
    from ..agent import run_testing_agent

    source = '''\
def process_payment(amount: float, user_id: str) -> dict:
    """Process a payment for a user."""
    if not user_id:
        raise ValueError("user_id required")
    if amount <= 0:
        raise ValueError("amount must be positive")
    return {"status": "ok", "amount": amount, "user_id": user_id}

def apply_discount(price: float, discount_pct: float) -> float:
    """Apply a percentage discount to a price."""
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("discount must be 0-100")
    return price * (1 - discount_pct / 100)
'''

    test_source = """\
def test_process_payment_happy_path():
    result = process_payment(100.0, "user_1")
    assert result["status"] == "ok"
"""

    diff = (
        f"""\
diff --git a/src/payments.py b/src/payments.py
index 0000000..1111111 100644
--- /dev/null
+++ b/src/payments.py
@@ -0,0 +1,{len(source.splitlines())} @@
"""
        + "\n".join(f"+{line}" for line in source.splitlines())
        + f"""
diff --git a/tests/test_payments.py b/tests/test_payments.py
index 0000000..2222222 100644
--- /dev/null
+++ b/tests/test_payments.py
@@ -0,0 +1,{len(test_source.splitlines())} @@
"""
        + "\n".join(f"+{line}" for line in test_source.splitlines())
    )

    agent_input = AgentInput(
        diff=diff,
        changed_files={
            "src/payments.py": source,
            "tests/test_payments.py": test_source,
        },
        repo_full_name="test-org/test-repo",
        pr_number=2,
        head_sha="abc1234",
        base_sha="def5678",
        pr_title="Add payment processing",
    )

    try:
        findings = run_testing_agent(agent_input)
    except anthropic.APIConnectionError as exc:
        pytest.skip(f"Skipping integration test: Anthropic API not reachable ({exc})")
    except anthropic.APIStatusError as exc:
        message = str(exc).lower()
        skippable_markers = (
            "credit balance is too low",
            "billing",
            "invalid api key",
            "authentication",
            "rate limit",
        )
        if exc.status_code in {400, 401, 402, 403, 429} or any(
            marker in message for marker in skippable_markers
        ):
            pytest.skip(f"Skipping integration test due to Anthropic account/API status: {exc}")
        raise

    assert isinstance(findings, list)
    # Should flag missing tests for negative amounts, empty user_id, apply_discount
    assert len(findings) >= 1
