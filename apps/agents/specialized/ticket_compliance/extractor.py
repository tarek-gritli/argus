from __future__ import annotations

import re

# GitHub: #42, Closes #42, Fixes #42 (case-insensitive, avoids URLs)
_GH_ISSUE_RE = re.compile(
    r"(?:(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+)?(?<![/\w])#(\d+)\b",
    re.IGNORECASE,
)

# Jira: PROJECT-123 (uppercase letters + digits, e.g. PROJ-42, MYTEAM-1000)
_JIRA_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")

# Linear: linear.app/…/issue/<IDENTIFIER> URLs
_LINEAR_URL_RE = re.compile(r"https://linear\.app/[^/]+/issue/([A-Za-z0-9_-]+)")

# Notion page: 32-char hex slug at end of notion.so or notion.site URLs
_NOTION_RE = re.compile(r"https://(?:www\.)?notion\.(?:so|site)/(?:[^/\s]+/)?[^/\s]*?([0-9a-fA-F]{32})(?:[?#]|$)")


def extract_ticket_refs(title: str, body: str) -> list[tuple[str, str]]:
    """
    Extract ticket references from PR title and body.

    Returns a deduplicated list of (provider, ticket_id) tuples.
    Providers: "github_issues", "jira", "linear", "notion".
    """
    text = f"{title}\n{body}"
    seen: set[tuple[str, str]] = set()
    results: list[tuple[str, str]] = []

    def _add(provider: str, ticket_id: str) -> None:
        key = (provider, ticket_id)
        if key not in seen:
            seen.add(key)
            results.append(key)

    for m in _LINEAR_URL_RE.finditer(text):
        _add("linear", m.group(1))

    for m in _NOTION_RE.finditer(text):
        _add("notion", m.group(1))

    for m in _GH_ISSUE_RE.finditer(text):
        _add("github_issues", m.group(1))

    # Jira: only match outside Linear/Notion URLs to avoid false positives
    for m in _JIRA_RE.finditer(text):
        _add("jira", m.group(1))

    return results
