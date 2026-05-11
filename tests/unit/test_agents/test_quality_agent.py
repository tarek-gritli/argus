"""
Tests for the quality agent.

Run with:
    uv run pytest tests/unit/test_agents/test_quality_agent.py -v
"""

from __future__ import annotations

from unittest.mock import patch

from specialized.quality.schemas import AgentInput
from specialized.quality.tools.ast_analyzer import analyze_file, run_static_analysis
from specialized.quality.tools.grep_patterns import scan_diff_patterns
from specialized.quality.validator import validate_findings

# ---------------------------------------------------------------------------
# AST analyzer tests
# ---------------------------------------------------------------------------


class TestAstAnalyzer:
    def test_simple_function_complexity(self):
        source = """\
def process(x):
    if x > 0:
        if x > 10:
            return "big"
        return "small"
    return "negative"
"""
        metrics = analyze_file("test.py", source)
        assert len(metrics.functions) == 1
        fn = metrics.functions[0]
        assert fn.name == "process"
        assert fn.cyclomatic_complexity >= 3
        assert fn.max_nesting_depth >= 2

    def test_magic_numbers_detected(self):
        source = """\
def compute(x):
    return x * 42 + 7
"""
        metrics = analyze_file("test.py", source)
        magic_values = [v for _, v in metrics.magic_numbers]
        assert 42 in magic_values
        assert 7 in magic_values

    def test_whitelist_numbers_not_flagged(self):
        source = """\
def compute(items):
    return len(items) * 1 + 0
"""
        metrics = analyze_file("test.py", source)
        magic_values = [v for _, v in metrics.magic_numbers]
        assert 0 not in magic_values
        assert 1 not in magic_values

    def test_unused_import_detected(self):
        source = """\
import os
import sys

def hello():
    print(sys.argv)
"""
        metrics = analyze_file("test.py", source)
        assert any("os" in imp for imp in metrics.unused_imports)

    def test_parse_error_handled(self):
        source = "def broken(:\n    pass"
        metrics = analyze_file("test.py", source)
        assert metrics.parse_error is not None
        assert metrics.functions == []

    def test_non_python_file_skipped(self):
        result = run_static_analysis({"README.md": "# Hello", "config.yaml": "key: val"})
        assert result.files == []

    def test_nesting_depth(self):
        source = """\
def deeply_nested():
    if True:
        for i in range(10):
            while True:
                if i > 5:
                    pass
"""
        metrics = analyze_file("test.py", source)
        assert metrics.functions[0].max_nesting_depth >= 4

    def test_prompt_context_renders(self):
        source = """\
def example(a, b, c):
    if a:
        return b
    return c
"""
        result = run_static_analysis({"example.py": source})
        context = result.to_prompt_context()
        assert "example.py" in context
        assert "example" in context
        assert "complexity=" in context


# ---------------------------------------------------------------------------
# Pattern scanner tests
# ---------------------------------------------------------------------------


class TestGrepPatterns:
    _DIFF = """\
@@ -1,3 +1,8 @@
 def process(data):
+    print(data)
+    # TODO: handle edge case
+    x = data * 3600
+    # def old_function():
+    #     pass
     return data
"""

    def test_detects_print(self):
        result = scan_diff_patterns(self._DIFF, "proc.py")
        names = [h.pattern_name for h in result.hits]
        assert "debug_print" in names

    def test_detects_todo(self):
        result = scan_diff_patterns(self._DIFF, "proc.py")
        names = [h.pattern_name for h in result.hits]
        assert "todo_fixme" in names

    def test_detects_commented_code(self):
        result = scan_diff_patterns(self._DIFF, "proc.py")
        names = [h.pattern_name for h in result.hits]
        assert "commented_code" in names

    def test_no_false_positives_on_context_lines(self):
        diff = """\
@@ -1,2 +1,2 @@
-def old():
+def new():
     pass
"""
        result = scan_diff_patterns(diff, "file.py")
        assert result.hits == []

    def test_prompt_context_renders_empty(self):
        result = scan_diff_patterns("@@ -1 +1 @@\n unchanged\n", "f.py")
        ctx = result.to_prompt_context()
        assert "no hits" in ctx

    def test_mutable_default_arg_detects_list(self):
        diff = "@@ -1 +1 @@\n+def fn(x=[]):\n    pass\n"
        result = scan_diff_patterns(diff, "f.py")
        names = [h.pattern_name for h in result.hits]
        assert "mutable_default_arg" in names

    def test_mutable_default_arg_detects_dict(self):
        diff = "@@ -1 +1 @@\n+def fn(x={}):\n    pass\n"
        result = scan_diff_patterns(diff, "f.py")
        names = [h.pattern_name for h in result.hits]
        assert "mutable_default_arg" in names

    def test_mutable_default_arg_no_false_positive_on_tuple(self):
        diff = "@@ -1 +1 @@\n+def fn(x=()):\n    pass\n"
        result = scan_diff_patterns(diff, "f.py")
        names = [h.pattern_name for h in result.hits]
        assert "mutable_default_arg" not in names


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestValidator:
    def _make_finding(self, **overrides) -> dict:
        base = {
            "agent": "quality",
            "severity": "medium",
            "file": "src/main.py",
            "line_start": 10,
            "line_end": 25,
            "title": "Function does too many things",
            "description": "This function handles both parsing and persistence.",
            "suggestion": "Extract persistence into a separate function.",
            "confidence": 0.85,
            "fix": None,
        }
        base.update(overrides)
        return base

    def test_valid_finding_passes(self):
        result = validate_findings([self._make_finding()])
        assert len(result) == 1

    def test_low_confidence_dropped(self):
        result = validate_findings([self._make_finding(confidence=0.3)])
        assert result == []

    def test_invalid_line_range_dropped(self):
        result = validate_findings([self._make_finding(line_start=0, line_end=-1)])
        assert result == []

    def test_missing_required_field_dropped(self):
        bad = self._make_finding()
        del bad["title"]
        result = validate_findings([bad])
        assert result == []

    def test_shallow_metric_echo_dropped(self):
        result = validate_findings([self._make_finding(title="Cyclomatic complexity is 15")])
        assert result == []

    def test_agent_field_forced_to_quality(self):
        result = validate_findings([self._make_finding(agent="security")])
        assert result[0]["agent"] == "quality"

    def test_severity_normalized(self):
        result = validate_findings([self._make_finding(severity="CRITICAL")])
        # Invalid severity → normalized to medium
        assert result[0]["severity"] == "medium"

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
        findings = [self._make_finding(title=f"Issue {i}") for i in range(30)]
        result = validate_findings(findings)
        assert len(result) <= 15


# ---------------------------------------------------------------------------
# _extract_file_diff
# ---------------------------------------------------------------------------


class TestExtractFileDiff:
    _MULTI_FILE_DIFF = """\
diff --git a/foo.py b/foo.py
index 0000000..1111111 100644
--- a/foo.py
+++ b/foo.py
@@ -1,1 +1,2 @@
+x = 1
diff --git a/bar.py b/bar.py
index 0000000..2222222 100644
--- a/bar.py
+++ b/bar.py
@@ -1,1 +1,2 @@
+y = 2
"""

    def test_extracts_first_file(self):
        from specialized.quality.agent import _extract_file_diff

        result = _extract_file_diff(self._MULTI_FILE_DIFF, "foo.py")
        assert "foo.py" in result
        assert "bar.py" not in result
        assert "+x = 1" in result

    def test_extracts_second_file(self):
        from specialized.quality.agent import _extract_file_diff

        result = _extract_file_diff(self._MULTI_FILE_DIFF, "bar.py")
        assert "bar.py" in result
        assert "foo.py" not in result
        assert "+y = 2" in result

    def test_missing_file_returns_empty(self):
        from specialized.quality.agent import _extract_file_diff

        result = _extract_file_diff(self._MULTI_FILE_DIFF, "missing.py")
        assert result == ""


# ---------------------------------------------------------------------------
# Full pipeline test (LLM mocked)
# ---------------------------------------------------------------------------

_MOCK_LLM_RESPONSE = """
[
  {
    "agent": "quality",
    "severity": "high",
    "file": "src/service.py",
    "line_start": 8,
    "line_end": 20,
    "title": "Function does too many things",
    "description": "do_everything handles data fetching, filtering, and result building in one deeply nested block.",
    "suggestion": "Extract filtering and result building into dedicated helpers.",
    "confidence": 0.88,
    "fix": null
  },
  {
    "agent": "quality",
    "severity": "low",
    "file": "src/service.py",
    "line_start": 22,
    "line_end": 22,
    "title": "Debug print left in code",
    "description": "print() call in process() will produce output in production.",
    "suggestion": "Replace with a logger call or remove.",
    "confidence": 0.95,
    "fix": null
  }
]
"""


def test_agent_pipeline():
    """Exercises the full agent pipeline with a mocked LLM — no API calls."""
    from specialized.quality.agent import run_quality_agent

    messy_source = """\
import os
import sys
import json

SECRET_KEY = "abc123"
MAX = 9999

def do_everything(user_id, data, db, cache, logger, mailer, config, feature_flags):
    if user_id:
        if data:
            if db:
                if cache:
                    result = []
                    for item in data:
                        if item > 0:
                            if item < MAX:
                                result.append(item * 42)
                    return result
    return None

def process(x):
    # TODO: fix this later
    print("processing", x)
    return x * 3600
"""

    diff = f"diff --git a/src/service.py b/src/service.py\nindex 0000000..1111111 100644\n--- /dev/null\n+++ b/src/service.py\n@@ -0,0 +1,{len(messy_source.splitlines())} @@\n" + "\n".join(f"+{line}" for line in messy_source.splitlines())

    agent_input = AgentInput(
        diff=diff,
        changed_files={"src/service.py": messy_source},
        repo_full_name="test-org/test-repo",
        pr_number=1,
        head_sha="abc1234",
        base_sha="def5678",
        pr_title="Add service module",
    )

    with patch("specialized.quality.agent._call_claude", return_value=_MOCK_LLM_RESPONSE):
        findings = run_quality_agent(agent_input)

    assert isinstance(findings, list)
    assert len(findings) >= 1
    assert all(f.agent == "quality" for f in findings)
    assert all(f.confidence >= 0.5 for f in findings)
    severities = {f.severity for f in findings}
    assert severities <= {"critical", "high", "medium", "low", "info"}
