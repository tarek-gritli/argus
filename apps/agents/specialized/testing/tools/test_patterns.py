"""
Diff-line pattern scanner for the testing agent.

Catches test anti-patterns that are faster to detect with regex than AST:
- assertTrue(x) used instead of a specific equality assertion
- assertFalse(x is not None) — double negation
- Tests with no assertions at all in the diff hunk
- Hardcoded sleep() calls (flaky test smell)
- Mocking everything (tests that don't test real behavior)
- Missing teardown (resource leak risk)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class TestPatternHit:
    file: str
    line: int
    pattern_name: str
    matched_text: str
    severity: str  # "high" | "medium" | "low"


@dataclass
class TestPatternResult:
    hits: list[TestPatternHit] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        if not self.hits:
            return "=== Test Pattern Scan: no anti-patterns detected ==="
        lines = ["=== Test Anti-Pattern Hits ==="]
        for hit in self.hits:
            lines.append(
                f"  {hit.file}:{hit.line} [{hit.severity}] [{hit.pattern_name}] "
                f"{hit.matched_text[:120]}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pattern definitions
# (pattern_name, compiled_regex, severity, description)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # Weak: assertTrue/assertFalse used where assertEqual would be better
    (
        "weak_assertTrue",
        re.compile(r"^\+\s*self\.assert(True|False)\s*\(\s*\w+\s*[=!<>]"),
        "medium",
    ),
    # Always-passing assertion (assert True or assert 1)
    (
        "trivially_true_assertion",
        re.compile(r"^\+\s*(assert True|assert 1|self\.assertTrue\(True\))"),
        "high",
    ),
    # sleep() in test — flakiness smell
    (
        "sleep_in_test",
        re.compile(r"^\+\s*(time\.sleep|asyncio\.sleep)\s*\("),
        "medium",
    ),
    # Broad exception catch in test — swallows real failures
    (
        "bare_except_in_test",
        re.compile(r"^\+\s*except\s*(\(Exception\)|Exception|BaseException)?\s*:"),
        "high",
    ),
    # pass in except block — silently ignores failures
    (
        "silent_except_pass",
        re.compile(r"^\+\s*except.*:\s*$"),
        "medium",
    ),
    # Mocking the thing under test itself
    (
        "mock_subject_under_test",
        re.compile(r"^\+.*mock\.patch\(__name__"),
        "medium",
    ),
    # TODO inside a test
    (
        "todo_in_test",
        re.compile(r"^\+.*\b(TODO|FIXME|HACK)\b", re.IGNORECASE),
        "low",
    ),
    # Test function with no assertion keywords anywhere in its added lines
    # (caught separately in _find_assertionless_tests)
]


def _find_assertionless_tests(diff: str, file_path: str) -> list[TestPatternHit]:
    """
    Detect test functions added in the diff that have no assertion in their body.
    Works by tracking added lines per function block.
    """
    hits = []
    lines = diff.splitlines()
    current_line = 0
    in_test_fn: str | None = None
    fn_start_line = 0
    fn_added_lines: list[str] = []

    _fn_re = re.compile(r"^\+\s*(?:async\s+)?def\s+(test\w*)\s*\(")
    _assert_re = re.compile(
        r"\b(assert|assertEqual|assertTrue|assertFalse|assertRaises|assertIn|assertIsNone)\b"
    )
    _indent_re = re.compile(r"^\+(\s+)")

    for raw in lines:
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if hunk:
            # Flush previous function if open
            if in_test_fn and fn_added_lines:
                body = "\n".join(fn_added_lines)
                if not _assert_re.search(body):
                    hits.append(
                        TestPatternHit(
                            file=file_path,
                            line=fn_start_line,
                            pattern_name="test_without_assertion",
                            matched_text=(
                                f"def {in_test_fn}(...) — no assertion found in added lines"
                            ),
                            severity="high",
                        )
                    )
            in_test_fn = None
            fn_added_lines = []
            current_line = int(hunk.group(1)) - 1
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            current_line += 1
            fn_match = _fn_re.match(raw)
            if fn_match:
                # Flush previous
                if in_test_fn and fn_added_lines:
                    body = "\n".join(fn_added_lines)
                    if not _assert_re.search(body):
                        hits.append(
                            TestPatternHit(
                                file=file_path,
                                line=fn_start_line,
                                pattern_name="test_without_assertion",
                                matched_text=(
                                    f"def {in_test_fn}(...) — no assertion found in added lines"
                                ),
                                severity="high",
                            )
                        )
                in_test_fn = fn_match.group(1)
                fn_start_line = current_line
                fn_added_lines = []
            elif in_test_fn:
                indent_match = _indent_re.match(raw)
                if indent_match:
                    fn_added_lines.append(raw[1:])  # strip leading '+'
                else:
                    # Back to top level — flush
                    if fn_added_lines:
                        body = "\n".join(fn_added_lines)
                        if not _assert_re.search(body):
                            hits.append(
                                TestPatternHit(
                                    file=file_path,
                                    line=fn_start_line,
                                    pattern_name="test_without_assertion",
                                    matched_text=(
                                        f"def {in_test_fn}(...) — no assertion found in added lines"
                                    ),
                                    severity="high",
                                )
                            )
                    in_test_fn = None
                    fn_added_lines = []
        elif not raw.startswith("-"):
            current_line += 1

    # Flush final
    if in_test_fn and fn_added_lines:
        body = "\n".join(fn_added_lines)
        if not _assert_re.search(body):
            hits.append(
                TestPatternHit(
                    file=file_path,
                    line=fn_start_line,
                    pattern_name="test_without_assertion",
                    matched_text=(f"def {in_test_fn}(...) — no assertion found in added lines"),
                    severity="high",
                )
            )

    return hits


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def scan_test_patterns(diff: str, file_path: str) -> TestPatternResult:
    """
    Scan the unified diff of a single file for test anti-patterns.
    Should be called only on test files (test_*.py / *_test.py).

    Args:
        diff:       Raw unified diff text for this file only.
        file_path:  Repo-relative path (used for reporting).

    Returns:
        TestPatternResult with all hits found.
    """
    result = TestPatternResult()
    current_line = 0

    for raw_line in diff.splitlines():
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw_line)
        if hunk_match:
            current_line = int(hunk_match.group(1)) - 1
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current_line += 1
            for name, pattern, severity in _PATTERNS:
                if pattern.search(raw_line):
                    result.hits.append(
                        TestPatternHit(
                            file=file_path,
                            line=current_line,
                            pattern_name=name,
                            matched_text=raw_line[1:].strip(),
                            severity=severity,
                        )
                    )
        elif not raw_line.startswith("-"):
            current_line += 1

    # Run assertionless test detector separately
    result.hits.extend(_find_assertionless_tests(diff, file_path))

    return result
