from __future__ import annotations

import httpx

_GRAPHQL_URL = "https://api.linear.app/graphql"

_QUERY = """
query IssueByIdentifier($identifier: String!) {
  issue(id: $identifier) {
    identifier
    title
    description
    url
  }
}
"""


def fetch_issue(access_token: str, identifier: str) -> dict | None:
    resp = httpx.post(
        _GRAPHQL_URL,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"query": _QUERY, "variables": {"identifier": identifier}},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("issue")
