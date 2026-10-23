from __future__ import annotations

from fastapi import HTTPException, Request


def require_owner(request: Request) -> None:
    """Route dependency: only the org's owner may change its configuration.

    AuthMiddleware puts the JWT's role on request.state; a missing role fails closed.
    """
    if getattr(request.state, "role", None) != "owner":
        raise HTTPException(status_code=403, detail="Only organization owners can do this")
