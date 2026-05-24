from __future__ import annotations

import re

# Matches: #42, Closes #42, Fixes #42, Resolves #42 (case-insensitive)
# Negative lookbehind avoids matching inside URLs (e.g. #issuecomment-123)
_GH_ISSUE_RE = re.compile(
    r"(?:(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+)?(?<![/\w])#(\d+)\b",
    re.IGNORECASE,
)


def extract_ticket_refs(title: str, body: str) -> list[tuple[str, str]]:
    """
    Extract GitHub issue references from PR title and body.

    Returns a deduplicated list of ("github_issues", issue_number) tuples.
    Extensible: future providers append their own (provider, id) tuples here.
    """
    text = f"{title}\n{body}"
    seen: set[tuple[str, str]] = set()
    results: list[tuple[str, str]] = []

    for m in _GH_ISSUE_RE.finditer(text):
        key = ("github_issues", m.group(1))
        if key not in seen:
            seen.add(key)
            results.append(key)

    return results
