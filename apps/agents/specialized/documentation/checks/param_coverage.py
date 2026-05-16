"""Static check: functions with parameters or return values but no docstring sections."""

from __future__ import annotations

import re
from typing import Any

FindingDict = dict[str, Any]

# Matches a def line with at least one non-self/cls parameter
_DEF_WITH_PARAMS_RE = re.compile(r"^\+\s*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)")
_TRIVIAL_PARAMS_RE = re.compile(r"^\s*(?:self|cls)?\s*$")

# Return type hints that suggest a non-trivial return
_RETURN_HINT_RE = re.compile(r"->\s*(?!None\b)(?!None\s*[|:])(\S)")

# Docstring presence within a few lines after the def (lines already have + stripped)
_DOCSTRING_OPEN_RE = re.compile(r'^\s*(?:"""|\'\'\')')
# Args/Returns sections inside a docstring
_ARGS_SECTION_RE = re.compile(r"Args:|Parameters:|:param\s", re.IGNORECASE)
_RETURNS_SECTION_RE = re.compile(r"Returns:|:returns:|:rtype:", re.IGNORECASE)

_PRIVATE_RE = re.compile(r"^_{1,2}[^_]")


def run_param_coverage_checks(context: dict[str, Any]) -> list[FindingDict]:
    """Find functions whose docstrings are missing Args or Returns sections."""
    diff: str = context.get("diff", "")
    findings: list[FindingDict] = []
    seen: set[tuple[str, int]] = set()

    current_file = ""
    hunk_new_start = 1
    non_removed_offset = 0
    lines = diff.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            hunk_new_start = 1
            non_removed_offset = 0
            i += 1
            continue

        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", line)
        if hunk_match:
            hunk_new_start = int(hunk_match.group(1))
            non_removed_offset = 0
            i += 1
            continue

        if line.startswith("-"):
            i += 1
            continue

        lineno = hunk_new_start + non_removed_offset
        non_removed_offset += 1

        def_match = _DEF_WITH_PARAMS_RE.match(line)
        if def_match:
            name = def_match.group(1)
            params_raw = def_match.group(2)

            if _PRIVATE_RE.match(name):
                i += 1
                continue

            # Non-trivial params?
            params = [p.strip().split(":")[0].split("=")[0].strip() for p in params_raw.split(",") if p.strip() and not _TRIVIAL_PARAMS_RE.match(p.strip())]
            has_return_hint = bool(_RETURN_HINT_RE.search(line))

            if not params and not has_return_hint:
                i += 1
                continue

            key = (current_file, lineno)
            if key in seen:
                i += 1
                continue

            # Collect the next ~20 added lines to find docstring content
            lookahead = _collect_added_lines(lines, i + 1, max_lines=20)
            docstring_body = "\n".join(lookahead)
            has_docstring = any(_DOCSTRING_OPEN_RE.match(ln) for ln in lookahead[:5])

            if not has_docstring:
                # No docstring at all — missing_docstrings checker handles this
                i += 1
                continue

            missing_args = bool(params) and not bool(_ARGS_SECTION_RE.search(docstring_body))
            missing_returns = has_return_hint and not _RETURNS_SECTION_RE.search(docstring_body)

            if missing_args or missing_returns:
                seen.add(key)
                findings.append(_make_finding(current_file, lineno, name, params, missing_args, missing_returns))

        i += 1

    return findings


def _collect_added_lines(lines: list[str], start: int, max_lines: int) -> list[str]:
    result = []
    for line in lines[start : start + max_lines * 2]:
        if line.startswith("+"):
            result.append(line[1:])
            if len(result) >= max_lines:
                break
    return result


def _make_finding(
    file: str,
    lineno: int,
    name: str,
    params: list[str],
    missing_args: bool,
    missing_returns: bool,
) -> FindingDict:
    missing_parts = []
    if missing_args:
        missing_parts.append("Args")
    if missing_returns:
        missing_parts.append("Returns")
    missing_str = " and ".join(missing_parts)

    param_list = ", ".join(f"`{p}`" for p in params[:5])
    suggestion_lines = ['    """', f"    Description of {name}.", ""]
    if missing_args:
        suggestion_lines += ["    Args:"] + [f"        {p}: Description." for p in params[:5]]
    if missing_returns:
        suggestion_lines += ["", "    Returns:", "        Description of the return value."]
    suggestion_lines.append('    """')

    return {
        "agent": "documentation",
        "severity": "medium",
        "file": file,
        "line_start": lineno,
        "line_end": lineno,
        "title": f"`{name}` docstring is missing {missing_str} section",
        "description": (f"`{name}` has parameters ({param_list}) but its docstring is missing a {missing_str} section. Callers cannot understand the expected inputs/outputs without reading the implementation."),
        "suggestion": "\n".join(suggestion_lines),
        "confidence": 0.82,
        "fix": None,
    }
