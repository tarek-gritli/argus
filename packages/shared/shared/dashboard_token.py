"""Lightweight HMAC-signed tokens for the public review dashboard URL.

No extra dependencies — uses stdlib hmac + hashlib + json + base64.
Token format: base64url(json_payload).hmac_sha256_hex
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

_DEFAULT_TTL = 7 * 24 * 3600  # 7 days


def sign(secret: str, repo_full_name: str, pr_number: int, ttl: int = _DEFAULT_TTL) -> str:
    payload = json.dumps({"repo": repo_full_name, "pr": pr_number, "exp": int(time.time()) + ttl})
    b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def verify(secret: str, token: str, repo_full_name: str, pr_number: int) -> bool:
    try:
        b64, sig = token.rsplit(".", 1)
        expected = hmac.new(secret.encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        padding = "=" * (-len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(b64 + padding).decode())
        return payload.get("repo") == repo_full_name and payload.get("pr") == pr_number and time.time() <= payload.get("exp", 0)
    except Exception:
        return False
