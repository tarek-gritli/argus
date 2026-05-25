from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_async_client(json_return):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = json_return
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx, mock_client


@pytest.mark.asyncio
async def test_exchange_code_returns_token():
    mock_ctx, mock_client = _mock_async_client({"access_token": "jira_tok_abc"})
    with patch("integrations.oauth.jira.httpx.AsyncClient", return_value=mock_ctx):
        from integrations.oauth.jira import exchange_code

        result = await exchange_code("code123", "CLIENT_ID", "CLIENT_SECRET", "https://app/callback")
    assert result["access_token"] == "jira_tok_abc"
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["grant_type"] == "authorization_code"


@pytest.mark.asyncio
async def test_get_accessible_resources_returns_list():
    resources = [{"id": "cloud-uuid-1", "url": "https://acme.atlassian.net", "name": "Acme"}]
    mock_ctx, mock_client = _mock_async_client(resources)
    with patch("integrations.oauth.jira.httpx.AsyncClient", return_value=mock_ctx):
        from integrations.oauth.jira import get_accessible_resources

        result = await get_accessible_resources("jira_tok_abc")
    assert result[0]["id"] == "cloud-uuid-1"
    mock_client.get.assert_called_once()
