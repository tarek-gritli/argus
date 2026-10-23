import base64
import hashlib
import hmac
import time


def validate_gitlab_token(header_value: str, secret: str) -> bool:
    """Check GitLab's plain X-Gitlab-Token header (available on every GitLab version)."""
    return bool(secret) and hmac.compare_digest(header_value.encode(), secret.encode())


def validate_gitlab_signature(payload: bytes, signature_header: str, webhook_id: str, timestamp: str, signing_token: str) -> bool:
    """Verify a Standard Webhooks signature (GitLab signing tokens, `whsec_<base64>`)."""
    # 5-minute window to prevent replay
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except (ValueError, TypeError):
        return False

    try:
        key = base64.b64decode(signing_token.removeprefix("whsec_"))
    except Exception:
        return False

    message = f"{webhook_id}.{timestamp}.".encode() + payload
    digest = hmac.new(key, message, hashlib.sha256).digest()
    computed = f"v1,{base64.b64encode(digest).decode()}"

    # GitLab may send several space-separated signatures
    return any(hmac.compare_digest(computed, s) for s in signature_header.split(" "))
