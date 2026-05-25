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


def test_fetch_issue_raises_on_graphql_errors():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"errors": [{"message": "Unauthorized"}], "data": None}

    with patch("integrations.linear.httpx.post", return_value=mock_response):
        from integrations.linear import fetch_issue

        with pytest.raises(ValueError, match="Linear GraphQL error"):
            fetch_issue("bad_token", "ENG-1")


def test_fetch_issue_returns_none_when_data_issue_is_null():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"data": {"issue": None}}

    with patch("integrations.linear.httpx.post", return_value=mock_response):
        from integrations.linear import fetch_issue

        result = fetch_issue("tok", "ENG-404")

    assert result is None
