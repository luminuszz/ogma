from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_openrouter_credits_disabled_when_key_missing(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with patch("src.main.httpx.AsyncClient") as mock_client_cls:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/openrouter/credits")

        assert response.status_code == 200
        data = response.json()
        assert data == {
            "enabled": False,
            "remaining": 0.0,
            "usage_daily": 0.0,
            "usage_total": 0.0,
            "limit": None,
        }
        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_openrouter_credits_disabled_when_key_empty(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "   ")

    with patch("src.main.httpx.AsyncClient") as mock_client_cls:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/openrouter/credits")

        assert response.status_code == 200
        assert response.json()["enabled"] is False
        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_openrouter_credits_success_standard(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkey123")

    fake_response = httpx.Response(
        status_code=200,
        json={
            "data": {
                "label": "Test Key",
                "usage": 2.45678,
                "usage_daily": 0.12345,
                "limit": 50.0,
                "limit_remaining": 47.54322,
                "is_free_tier": False,
            }
        },
        request=httpx.Request("GET", "https://openrouter.ai/api/v1/auth/key"),
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=fake_response)

    with patch("src.main.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/openrouter/credits")

        assert response.status_code == 200
        data = response.json()
        assert data == {
            "enabled": True,
            "remaining": 47.5432,
            "usage_daily": 0.1235,
            "usage_total": 2.4568,
            "limit": 50.0,
        }
        mock_client.get.assert_called_once_with(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": "Bearer sk-or-v1-testkey123"},
        )


@pytest.mark.asyncio
async def test_openrouter_credits_fallback_total_credits(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkey123")

    fake_response = httpx.Response(
        status_code=200,
        json={
            "data": {
                "limit_remaining": None,
                "total_credits": 10.0,
                "usage": 3.25,
                "usage_daily": 0.5,
                "limit": None,
            }
        },
        request=httpx.Request("GET", "https://openrouter.ai/api/v1/auth/key"),
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=fake_response)

    with patch("src.main.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/openrouter/credits")

        assert response.status_code == 200
        data = response.json()
        assert data == {
            "enabled": True,
            "remaining": 6.75,
            "usage_daily": 0.5,
            "usage_total": 3.25,
            "limit": None,
        }


@pytest.mark.asyncio
async def test_openrouter_credits_fallback_effective_budget(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkey123")

    fake_response = httpx.Response(
        status_code=200,
        json={
            "data": {
                "limit_remaining": None,
                "total_credits": None,
                "effective_budget": {"remaining_usd": 12.34567},
                "usage": 1.0,
                "usage_daily": 0.0,
                "limit": None,
            }
        },
        request=httpx.Request("GET", "https://openrouter.ai/api/v1/auth/key"),
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=fake_response)

    with patch("src.main.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/openrouter/credits")

        assert response.status_code == 200
        data = response.json()
        assert data == {
            "enabled": True,
            "remaining": 12.3457,
            "usage_daily": 0.0,
            "usage_total": 1.0,
            "limit": None,
        }


@pytest.mark.asyncio
async def test_openrouter_credits_error_401(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-invalid-key")

    error_response = httpx.Response(
        status_code=401,
        text="Invalid API key",
        request=httpx.Request("GET", "https://openrouter.ai/api/v1/auth/key"),
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=error_response)

    with patch("src.main.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/openrouter/credits")

        assert response.status_code == 503
        data = response.json()
        assert "OpenRouter API error (401)" in data["detail"]


@pytest.mark.asyncio
async def test_openrouter_credits_error_timeout(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkey123")

    timeout_err = httpx.TimeoutException(
        "Request timed out",
        request=httpx.Request("GET", "https://openrouter.ai/api/v1/auth/key"),
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(side_effect=timeout_err)

    with patch("src.main.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/openrouter/credits")

        assert response.status_code == 503
        data = response.json()
        assert "Erro de conexão com OpenRouter" in data["detail"]
