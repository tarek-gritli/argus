"""Static check: public functions and classes added without a docstring."""

from __future__ import annotations

import re
from typing import Any

FindingDict = dict[str, Any]

# Matches `def name(` or `async def name(` in added diff lines
_DEF_RE = re.compile(r"^\+\s*(?:async\s+)?def\s+(\w+)\s*\(")
# Matches `class Name` in added diff lines
_CLASS_RE = re.compile(r"^\+\s*class\s+(\w+)")
# Added line that opens a docstring
_DOCSTRING_RE = re.compile(r'^\+\s*(?:"""|\'\'\')')
# Private by convention
_PRIVATE_RE = re.compile(r"^_{1,2}[^_]")


def run_missing_docstring_checks(context: dict[str, Any]) -> list[FindingDict]:
    """Scan diff lines for public defs/classes missing an immediately following docstring."""
    diff: str = context.get("diff", "")
    findings: list[FindingDict] = []
    seen: set[tuple[str, int]] = set()

    current_file = ""
    lines = diff.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            i += 1
            continue

        if line.startswith("@@ "):
            i += 1
            continue

        def_match = _DEF_RE.match(line)
        class_match = _CLASS_RE.match(line)
        match = def_match or class_match
        name = match.group(1) if match else None

        if match and name and not _PRIVATE_RE.match(name):
            # Find line number from the most recent @@ header
            lineno = _estimate_lineno(lines, i)
            key = (current_file, lineno)
            if key not in seen:
                seen.add(key)
                # Look ahead: find the next added non-empty, non-decorator line
                has_docstring = _next_added_line_is_docstring(lines, i + 1)
                if not has_docstring:
                    kind = "class" if class_match else "function"
                    findings.append(_make_finding(current_file, lineno, name, kind))

        i += 1

    return findings


def _next_added_line_is_docstring(lines: list[str], start: int) -> bool:
    """Return True if the next meaningful added line opens a docstring."""
    for line in lines[start : start + 6]:
        # Strip exactly the diff marker (+/space/minus) to get content
        stripped = line[1:].lstrip() if line and line[0] in ("+", " ", "-") else line.lstrip()
        if not stripped:
            continue
        # Skip the closing paren / colon of the def — look for body
        if stripped.startswith(")") or stripped == ":":
            continue
        return bool(_DOCSTRING_RE.match(line))
    return False


def _estimate_lineno(lines: list[str], def_index: int) -> int:
    """Walk back to the last @@ header and compute approximate line number."""
    new_start = 1
    offset = 0
    for j in range(def_index - 1, -1, -1):
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", lines[j])
        if hunk:
            new_start = int(hunk.group(1))
            # Count added/context lines between hunk start and def_index
            for k in range(j + 1, def_index):
                if not lines[k].startswith("-"):
                    offset += 1
            return new_start + offset
    return 1


def _make_finding(file: str, lineno: int, name: str, kind: str) -> FindingDict:
    return {
        "agent": "documentation",
        "severity": "high" if kind == "function" else "medium",
        "file": file,
        "line_start": lineno,
        "line_end": lineno,
        "title": f"Public {kind} `{name}` has no docstring",
        "description": (f"`{name}` is a public {kind} added in this PR without a docstring. Future contributors cannot understand its contract without reading the implementation."),
        "suggestion": (f'Add a docstring immediately after the `{kind}` declaration:\n    """\n    Brief description of what {name} does.\n\n    Args:\n        param_name: Description.\n\n    Returns:\n        Description of the return value.\n    """'),
        "confidence": 0.85,
        "fix": None,
    }
