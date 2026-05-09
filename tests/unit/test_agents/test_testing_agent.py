"""
Tests for the testing agent.

Run with:
    uv run pytest tests/unit/test_agents/test_testing_agent.py -v
"""

from __future__ import annotations

from unittest.mock import patch

from specialized.testing.schemas import AgentInput
from specialized.testing.tools.coverage_analyzer import analyze_file, run_coverage_analysis
from specialized.testing.tools.test_patterns import scan_test_patterns
from specialized.testing.validator import validate_findings

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
        result = run_coverage_analysis({"src/service.py": "def process_payment(amount): pass"})
        untested = result.untested_symbols
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
        assert not any(s.name == "process_payment" for s, _ in untested)

    def test_prompt_context_warns_no_test_files(self):
        result = run_coverage_analysis({"src/foo.py": "def foo(): pass"})
        context = result.to_prompt_context()
        assert "NONE" in context or "no test files" in context.lower()

    def test_prompt_context_includes_symbol_names(self):
        result = run_coverage_analysis({"src/foo.py": "def my_function(): pass\ndef another(): pass"})
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
        diff = "@@ -1,3 +1,5 @@\n def test_x():\n+    try:\n+        do_thing()\n+    except Exception:\n+        pass\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "bare_except_in_test" in names

    def test_detects_bare_except_no_type(self):
        diff = "@@ -1,3 +1,4 @@\n def test_x():\n+    try:\n+        do_thing()\n+    except:\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "bare_except_in_test" in names

    def test_no_false_positive_on_specific_except(self):
        diff = "@@ -1,3 +1,4 @@\n def test_x():\n+    try:\n+        do_thing()\n+    except ValueError:\n"
        result = scan_test_patterns(diff, "tests/test_x.py")
        names = [h.pattern_name for h in result.hits]
        assert "bare_except_in_test" not in names
        assert "silent_except_pass" not in names

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
            "suggestion": ("Add test_process_payment_raises_on_negative_amount that calls process_payment(-1) and asserts ValueError is raised."),
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

    def test_non_dict_item_dropped_without_crash(self):
        result = validate_findings(["not a dict", 42, None, self._make_finding()])  # type: ignore[list-item]
        assert len(result) == 1

    def test_string_line_numbers_coerced(self):
        result = validate_findings([self._make_finding(line_start="10", line_end="30")])
        assert len(result) == 1

    def test_non_numeric_confidence_dropped_without_crash(self):
        result = validate_findings([self._make_finding(confidence="high")])
        assert result == []

    def test_none_confidence_dropped_without_crash(self):
        result = validate_findings([self._make_finding(confidence=None)])
        assert result == []


# ---------------------------------------------------------------------------
# _extract_file_diff tests
# ---------------------------------------------------------------------------


class TestExtractFileDiff:
    _MULTI_FILE_DIFF = """\
diff --git a/src/payments.py b/src/payments.py
index 0000000..1111111 100644
--- a/src/payments.py
+++ b/src/payments.py
@@ -1,1 +1,2 @@
+x = 1
diff --git a/tests/test_payments.py b/tests/test_payments.py
index 0000000..2222222 100644
--- a/tests/test_payments.py
+++ b/tests/test_payments.py
@@ -1,1 +1,2 @@
+def test_x(): pass
"""

    def test_extracts_first_file(self):
        from specialized.testing.agent import _extract_file_diff

        result = _extract_file_diff(self._MULTI_FILE_DIFF, "src/payments.py")
        assert "src/payments.py" in result
        assert "test_payments.py" not in result
        assert "+x = 1" in result

    def test_extracts_second_file(self):
        from specialized.testing.agent import _extract_file_diff

        result = _extract_file_diff(self._MULTI_FILE_DIFF, "tests/test_payments.py")
        assert "test_payments.py" in result
        assert "src/payments.py" not in result
        assert "+def test_x(): pass" in result

    def test_missing_file_returns_empty(self):
        from specialized.testing.agent import _extract_file_diff

        result = _extract_file_diff(self._MULTI_FILE_DIFF, "missing.py")
        assert result == ""


# ---------------------------------------------------------------------------
# Full pipeline test (LLM mocked)
# ---------------------------------------------------------------------------

_MOCK_LLM_RESPONSE = """
[
  {
    "agent": "testing",
    "severity": "high",
    "file": "src/payments.py",
    "line_start": 1,
    "line_end": 10,
    "title": "apply_discount has no test for out-of-range discount",
    "description": "The function raises ValueError for discounts outside 0-100, but no test covers this edge case.",
    "suggestion": "Add test_apply_discount_raises_on_invalid_pct that calls apply_discount(100, -1) and asserts ValueError.",
    "confidence": 0.88,
    "fix": null
  }
]
"""

_SOURCE = """\
def process_payment(amount: float, user_id: str) -> dict:
    if not user_id:
        raise ValueError("user_id required")
    if amount <= 0:
        raise ValueError("amount must be positive")
    return {"status": "ok", "amount": amount, "user_id": user_id}

def apply_discount(price: float, discount_pct: float) -> float:
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("discount must be 0-100")
    return price * (1 - discount_pct / 100)
"""

_TEST_SOURCE = """\
def test_process_payment_happy_path():
    result = process_payment(100.0, "user_1")
    assert result["status"] == "ok"
"""


def test_agent_pipeline():
    """Exercises the full agent pipeline with a mocked LLM — no API calls."""
    from specialized.testing.agent import run_testing_agent

    diff = (
        f"diff --git a/src/payments.py b/src/payments.py\n"
        f"index 0000000..1111111 100644\n--- /dev/null\n+++ b/src/payments.py\n"
        f"@@ -0,0 +1,{len(_SOURCE.splitlines())} @@\n" + "\n".join(f"+{line}" for line in _SOURCE.splitlines()) + f"\ndiff --git a/tests/test_payments.py b/tests/test_payments.py\n"
        f"index 0000000..2222222 100644\n--- /dev/null\n+++ b/tests/test_payments.py\n"
        f"@@ -0,0 +1,{len(_TEST_SOURCE.splitlines())} @@\n" + "\n".join(f"+{line}" for line in _TEST_SOURCE.splitlines())
    )

    agent_input = AgentInput(
        diff=diff,
        changed_files={
            "src/payments.py": _SOURCE,
            "tests/test_payments.py": _TEST_SOURCE,
        },
        repo_full_name="test-org/test-repo",
        pr_number=2,
        head_sha="abc1234",
        base_sha="def5678",
        pr_title="Add payment processing",
    )

    with patch("specialized.testing.agent._call_claude", return_value=_MOCK_LLM_RESPONSE):
        findings = run_testing_agent(agent_input)

    assert isinstance(findings, list)
    assert len(findings) >= 1
    assert all(f.agent == "testing" for f in findings)
    assert all(f.confidence >= 0.5 for f in findings)
    severities = {f.severity for f in findings}
    assert severities <= {"critical", "high", "medium", "low", "info"}
