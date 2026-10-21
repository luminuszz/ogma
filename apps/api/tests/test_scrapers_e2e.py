from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_scraper_full_flow_preview_and_start(monkeypatch):
    # Mock LycantoonsProvider.extract_manga_info to avoid real browser launch in test
    from src.scrapers.base import ChapterItem, MangaPreview
    from src.scrapers.providers.lycantoons import LycantoonsProvider

    async def mock_extract(self, url):
        return MangaPreview(
            provider="lycantoons",
            manga_id="lycantoons:mock-series",
            title="Mock Series",
            cover_url="https://example.com/cover.webp",
            chapters=[
                ChapterItem(
                    id="lycantoons:mock-series:1",
                    number="1",
                    title="Capítulo 1",
                    url="https://lycantoons.com/series/mock-series/1",
                )
            ],
        )

    monkeypatch.setattr(LycantoonsProvider, "extract_manga_info", mock_extract)

    # Mock DB session and redis_pool to allow offline integration testing
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_res)

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("src.main.AsyncSessionLocal", lambda: MockSessionContext())

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()
    monkeypatch.setattr("src.main.redis_pool", mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Preview
        preview_resp = await ac.post("/api/scraper/preview", json={"url": "https://lycantoons.com/series/mock-series"})
        assert preview_resp.status_code == 200
        data = preview_resp.json()
        assert data["title"] == "Mock Series"
        assert len(data["chapters"]) == 1

        # 2. Start
        start_resp = await ac.post("/api/scraper/start", json={
            "provider": "lycantoons",
            "mangaId": data["mangaId"],
            "title": data["title"],
            "chapters": data["chapters"]
        })
        assert start_resp.status_code == 200
        assert start_resp.json()["status"] == "queued"
        assert start_resp.json()["count"] == 1

        mock_redis.enqueue_job.assert_called_once_with(
            "scrape_and_download_chapter",
            "lycantoons",
            "lycantoons:mock-series:1",
            "https://lycantoons.com/series/mock-series/1",
            False,
            _job_id="scrape_lycantoons:mock-series:1",
        )
