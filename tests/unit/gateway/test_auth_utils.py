from unittest.mock import patch

import pytest
from auth_utils import create_jwt, decode_jwt


def test_round_trip():
    with patch("auth_utils.get_settings") as mock:
        mock.return_value.jwt_secret_key = "test-secret-key-32-bytes-padding!"
        mock.return_value.jwt_ttl_seconds = 3600
        token = create_jwt(user_id="u1", org_id="o1", role="owner")
        payload = decode_jwt(token)
        assert payload["sub"] == "u1"
        assert payload["oid"] == "o1"
        assert payload["role"] == "owner"


def test_expired_token_raises():
    with patch("auth_utils.get_settings") as mock:
        mock.return_value.jwt_secret_key = "test-secret-key-32-bytes-padding!"
        mock.return_value.jwt_ttl_seconds = -1  # already expired
        token = create_jwt(user_id="u1", org_id="o1", role="owner")
        with pytest.raises(Exception):
            decode_jwt(token)
