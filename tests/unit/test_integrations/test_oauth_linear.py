from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_exchange_code_returns_access_token():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"access_token": "lin_oauth_abc", "token_type": "Bearer"}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("integrations.oauth.linear.httpx.AsyncClient", return_value=mock_ctx):
        from integrations.oauth.linear import exchange_code

        result = await exchange_code("code123", "CLIENT_ID", "CLIENT_SECRET", "https://app/callback")

    assert result["access_token"] == "lin_oauth_abc"
    _, kwargs = mock_client.post.call_args
    assert kwargs["data"]["grant_type"] == "authorization_code"
    assert kwargs["data"]["code"] == "code123"
