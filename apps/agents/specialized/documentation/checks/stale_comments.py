"""Static check: stale, leftover, or low-value comments added in the diff."""

from __future__ import annotations

import re
from typing import Any

FindingDict = dict[str, Any]

# Debt markers without a ticket reference
_DEBT_RE = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
_TICKET_RE = re.compile(r"[A-Z]+-\d+|#\d+|https?://")

# Commented-out code heuristics: line starts with # and looks like code.
# Intentionally simple — false positives on explanatory comments are acceptable
# because the LLM validation pass will filter them if confidence is too low.
_COMMENTED_CODE_RE = re.compile(
    r"#\s*(?:(?:def |class |import |from |return |if |for |while |with )|"
    r"(?:\w+\s*=\s*\w)|(?:\w+\.\w+\())"
)


def run_stale_comment_checks(context: dict[str, Any]) -> list[FindingDict]:
    """Detect debt markers and commented-out code in added diff lines."""
    diff: str = context.get("diff", "")
    findings: list[FindingDict] = []
    seen: set[tuple[str, int]] = set()

    current_file = ""
    hunk_new_start = 1
    added_offset = 0

    for raw_line in diff.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:].strip()
            hunk_new_start = 1
            added_offset = 0
            continue

        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", raw_line)
        if hunk_match:
            hunk_new_start = int(hunk_match.group(1))
            added_offset = 0
            continue

        if raw_line.startswith("-"):
            continue

        if not raw_line.startswith("+"):
            added_offset += 1
            continue

        lineno = hunk_new_start + added_offset
        added_offset += 1
        content = raw_line[1:]

        key = (current_file, lineno)
        if key in seen:
            continue

        debt_match = _DEBT_RE.search(content)
        if debt_match:
            marker = debt_match.group(1).upper()
            has_ticket = bool(_TICKET_RE.search(content))
            seen.add(key)
            findings.append(_make_debt_finding(current_file, lineno, marker, content.strip(), has_ticket))
            continue

        if _COMMENTED_CODE_RE.search(content):
            seen.add(key)
            findings.append(_make_commented_code_finding(current_file, lineno, content.strip()))

    return findings


def _make_debt_finding(
    file: str,
    lineno: int,
    marker: str,
    content: str,
    has_ticket: bool,
) -> FindingDict:
    severity = "low" if has_ticket else "medium"
    suggestion = "Add a ticket reference so this can be tracked (e.g. `# TODO(PROJ-123): ...`)." if not has_ticket else "Ensure this is tracked in your issue tracker before merging."
    return {
        "agent": "documentation",
        "severity": severity,
        "file": file,
        "line_start": lineno,
        "line_end": lineno,
        "title": f"{marker} comment added without a ticket reference" if not has_ticket else f"{marker} comment introduced",
        "description": (f"A `{marker}` marker was added in this PR: `{content[:120]}`. " + ("No issue tracker reference was found, making it invisible to future triage." if not has_ticket else "Ensure the linked ticket is still open and relevant.")),
        "suggestion": suggestion,
        "confidence": 0.88 if not has_ticket else 0.65,
        "fix": None,
    }


def _make_commented_code_finding(file: str, lineno: int, content: str) -> FindingDict:
    return {
        "agent": "documentation",
        "severity": "low",
        "file": file,
        "line_start": lineno,
        "line_end": lineno,
        "title": "Commented-out code block added",
        "description": (f"This line appears to be commented-out code: `{content[:120]}`. Commented-out code adds noise, confuses readers, and is better tracked via git history."),
        "suggestion": "Remove the commented-out code. Use git history or a branch to preserve it if needed.",
        "confidence": 0.72,
        "fix": None,
    }
