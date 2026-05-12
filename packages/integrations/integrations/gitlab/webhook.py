import base64
import hashlib
import hmac
import time


def validate_gitlab_signature(payload: bytes, signature_header: str, webhook_id: str, timestamp: str, signing_token: str) -> bool:
    # 1. Timing check (5-minute window to prevent replay attacks)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except (ValueError, TypeError):
        return False

    # 2. Decode the signing token
    # GitLab tokens are 'whsec_base64...'
    token_clean = signing_token.replace("whsec_", "")
    try:
        key = base64.b64decode(token_clean)
    except Exception:
        return False

    # 3. Construct the message: "{id}.{timestamp}.{body}"
    message = f"{webhook_id}.{timestamp}.".encode() + payload

    # 4. Compute the HMAC-SHA256
    digest = hmac.new(key, message, hashlib.sha256).digest()
    computed_signature = f"v1,{base64.b64encode(digest).decode()}"

    # 5. Constant-time comparison against list of signatures
    # (GitLab may send multiple signatures separated by spaces)
    received_signatures = signature_header.split(" ")
    return any(hmac.compare_digest(computed_signature, s) for s in received_signatures)
