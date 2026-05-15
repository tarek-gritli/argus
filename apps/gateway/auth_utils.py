from datetime import datetime, timezone

import jwt
from shared.config import get_settings


def create_jwt(user_id: str, org_id: str, role: str) -> str:
    settings = get_settings()
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": user_id,
        "oid": org_id,
        "role": role,
        "iat": now,
        "exp": now + settings.jwt_ttl_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
