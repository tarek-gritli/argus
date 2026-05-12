"""Static check: new public modules or env vars added without README/docs update."""

from __future__ import annotations

import re
from typing import Any

FindingDict = dict[str, Any]

# Files that count as documentation
_DOC_FILES_RE = re.compile(
    r"(?:^|/)(?:README|CHANGELOG|CONTRIBUTING|docs?/.*)\.(md|rst|txt)$",
    re.IGNORECASE,
)

# New public Python modules (not test, not __init__)
_PUBLIC_MODULE_RE = re.compile(r"^(?!.*(test_|_test\.|__init__)).*\.py$")

# Environment variable patterns in added lines
_ENVVAR_RE = re.compile(r'os\.(?:environ\.get|getenv)\(["\'](\w+)["\']|settings\.(\w+)\b')

# Config key patterns
_CONFIG_KEY_RE = re.compile(r'["\']([A-Z][A-Z0-9_]{3,})["\']')


def run_readme_gap_checks(context: dict[str, Any]) -> list[FindingDict]:
    """Detect new public modules and undocumented env vars when docs weren't updated."""
    diff: str = context.get("diff", "")
    changed_files: dict[str, str] = context.get("changed_files", {})
    findings: list[FindingDict] = []

    has_doc_change = any(_DOC_FILES_RE.search(f) for f in changed_files)

    new_public_modules = [f for f in changed_files if _PUBLIC_MODULE_RE.match(f.split("/")[-1]) and _is_new_file(diff, f) and not f.startswith("tests/")]

    if new_public_modules and not has_doc_change:
        for module_path in new_public_modules[:3]:  # cap to avoid noise
            findings.append(_make_module_finding(module_path))

    # Scan added lines for env var references
    env_vars = _extract_new_env_vars(diff)
    if env_vars and not has_doc_change:
        for var_name, file_path, lineno in env_vars[:3]:
            findings.append(_make_envvar_finding(var_name, file_path, lineno))

    return findings


def _is_new_file(diff: str, file_path: str) -> bool:
    return "--- /dev/null" in diff and f"+++ b/{file_path}" in diff


def _extract_new_env_vars(diff: str) -> list[tuple[str, str, int]]:
    results: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    current_file = ""
    hunk_new_start = 1
    offset = 0

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            hunk_new_start = 1
            offset = 0
            continue

        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", line)
        if hunk_match:
            hunk_new_start = int(hunk_match.group(1))
            offset = 0
            continue

        if line.startswith("-"):
            continue

        lineno = hunk_new_start + offset
        if not line.startswith("+"):
            offset += 1
            continue

        offset += 1
        content = line[1:]
        m = _ENVVAR_RE.search(content)
        if m:
            var_name = m.group(1) or m.group(2)
            if var_name and var_name not in seen:
                seen.add(var_name)
                results.append((var_name, current_file, lineno))

    return results


def _make_module_finding(module_path: str) -> FindingDict:
    return {
        "agent": "documentation",
        "severity": "medium",
        "file": module_path,
        "line_start": 1,
        "line_end": 1,
        "title": f"New module `{module_path}` has no README entry",
        "description": (f"A new public module `{module_path}` was added but no README, CHANGELOG, or docs file was updated. New contributors won't know this module exists or how to use it."),
        "suggestion": ("Add a brief entry to the relevant README.md or docs/ file describing the module's purpose, public API, and a usage example."),
        "confidence": 0.70,
        "fix": None,
    }


def _make_envvar_finding(var_name: str, file_path: str, lineno: int) -> FindingDict:
    return {
        "agent": "documentation",
        "severity": "high",
        "file": file_path,
        "line_start": lineno,
        "line_end": lineno,
        "title": f"Environment variable `{var_name}` is undocumented",
        "description": (f"The environment variable `{var_name}` is referenced in this PR but no documentation file (README, .env.example, or docs/) was updated. Operators deploying this service won't know this variable is required."),
        "suggestion": (f"Add `{var_name}` to your `.env.example` and document its purpose, type, default value, and whether it is required in the README."),
        "confidence": 0.80,
        "fix": None,
    }
