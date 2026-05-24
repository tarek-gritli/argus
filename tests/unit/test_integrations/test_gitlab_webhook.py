import base64
import hashlib
import hmac
import time

from integrations.gitlab.webhook import validate_gitlab_signature


def _generate_valid_signature(payload: bytes, webhook_id: str, timestamp: str, token_b64: str) -> str:
    key = base64.b64decode(token_b64)
    message = f"{webhook_id}.{timestamp}.".encode() + payload
    digest = hmac.new(key, message, hashlib.sha256).digest()
    return f"v1,{base64.b64encode(digest).decode()}"


def test_validate_gitlab_signature_valid():
    payload = b'{"event":"merge_request"}'
    webhook_id = "test-webhook"
    timestamp = str(int(time.time()))
    token_b64 = base64.b64encode(b"secret_key").decode()
    signing_token = f"whsec_{token_b64}"

    signature = _generate_valid_signature(payload, webhook_id, timestamp, token_b64)

    assert validate_gitlab_signature(payload, signature, webhook_id, timestamp, signing_token) is True


def test_validate_gitlab_signature_invalid_signature():
    payload = b'{"event":"merge_request"}'
    webhook_id = "test-webhook"
    timestamp = str(int(time.time()))
    token_b64 = base64.b64encode(b"secret_key").decode()
    signing_token = f"whsec_{token_b64}"

    signature = "v1,invalid_signature"

    assert validate_gitlab_signature(payload, signature, webhook_id, timestamp, signing_token) is False


def test_validate_gitlab_signature_expired_timestamp():
    payload = b'{"event":"merge_request"}'
    webhook_id = "test-webhook"
    # 6 minutes ago (limit is 5 mins)
    timestamp = str(int(time.time()) - 360)
    token_b64 = base64.b64encode(b"secret_key").decode()
    signing_token = f"whsec_{token_b64}"

    signature = _generate_valid_signature(payload, webhook_id, timestamp, token_b64)

    assert validate_gitlab_signature(payload, signature, webhook_id, timestamp, signing_token) is False


def test_validate_gitlab_signature_invalid_timestamp_format():
    payload = b'{"event":"merge_request"}'
    assert validate_gitlab_signature(payload, "sig", "id", "not-an-int", "token") is False


def test_validate_gitlab_signature_invalid_token_b64():
    payload = b'{"event":"merge_request"}'
    timestamp = str(int(time.time()))
    assert validate_gitlab_signature(payload, "sig", "id", timestamp, "whsec_!invalid_b64!") is False
