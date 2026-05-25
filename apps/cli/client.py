from __future__ import annotations

import httpx

_DEFAULT_BASE = "http://localhost:8000"


def make_client(token: str | None = None, base_url: str = _DEFAULT_BASE) -> httpx.Client:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=base_url, headers=headers, timeout=120)
