from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app
from src.scrapers.base import ChapterItem, MangaPreview


@pytest.mark.asyncio
async def test_scraper_preview_returns_400_for_unsupported_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/scraper/preview", json={"url": "https://unknown.com/series/test"})
        assert response.status_code == 400
        assert "Nenhum provedor suportado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_scraper_preview_missing_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/scraper/preview", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_scraper_preview_success():
    fake_preview = MangaPreview(
        provider="lycantoons",
        manga_id="test-slug",
        title="Test Title",
        cover_url="https://img.test/cover.jpg",
        chapters=[
            ChapterItem(
                id="ch-1",
                number="1",
                title="Chapter 1",
                url="https://lycantoons.com/obra/test-slug/capitulo-1",
            )
        ],
    )
    mock_provider = MagicMock()
    mock_provider.can_handle.return_value = True
    mock_provider.extract_manga_info = AsyncMock(return_value=fake_preview)

    with patch("src.main.get_registry") as mock_get_registry:
        mock_registry = MagicMock()
        mock_registry.get_provider_for_url.return_value = mock_provider
        mock_get_registry.return_value = mock_registry

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/scraper/preview",
                json={"url": "https://lycantoons.com/obra/test-slug"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["supported"] is True
            assert data["provider"] == "lycantoons"
            assert data["mangaId"] == "test-slug"
            assert data["title"] == "Test Title"
            assert data["coverUrl"] == "https://img.test/cover.jpg"
            assert len(data["chapters"]) == 1
            assert data["chapters"][0]["id"] == "ch-1"


@pytest.mark.asyncio
async def test_scraper_preview_extraction_error():
    mock_provider = MagicMock()
    mock_provider.can_handle.return_value = True
    mock_provider.extract_manga_info = AsyncMock(side_effect=RuntimeError("Extraction failed"))

    with patch("src.main.get_registry") as mock_get_registry:
        mock_registry = MagicMock()
        mock_registry.get_provider_for_url.return_value = mock_provider
        mock_get_registry.return_value = mock_registry

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/scraper/preview",
                json={"url": "https://lycantoons.com/obra/test-slug"},
            )
            assert response.status_code == 500
            assert "Erro ao extrair dados da obra: Extraction failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_scraper_start_invalid_provider():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/scraper/start",
            json={
                "provider": "nonexistent",
                "mangaId": "m1",
                "title": "Title",
                "chapters": [],
            },
        )
        assert response.status_code == 400
        assert "Provedor inválido" in response.json()["detail"]


@pytest.mark.asyncio
async def test_scraper_start_success():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock()
    mock_manga_res = MagicMock()
    mock_manga_res.scalar_one_or_none.return_value = None
    mock_chapter_res = MagicMock()
    mock_chapter_res.scalar_one_or_none.return_value = None
    mock_session.execute.side_effect = [mock_manga_res, mock_chapter_res]

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_redis = AsyncMock()

    with patch("src.main.get_registry") as mock_get_registry, \
         patch("src.main.AsyncSessionLocal", return_value=MockSessionContext()), \
         patch("src.main.redis_pool", mock_redis):

        mock_registry = MagicMock()
        mock_registry.list_providers.return_value = ["lycantoons"]
        mock_get_registry.return_value = mock_registry

        payload = {
            "provider": "lycantoons",
            "mangaId": "test-slug",
            "title": "Test Title",
            "chapters": [
                {
                    "id": "ch-1",
                    "number": "1",
                    "url": "https://lycantoons.com/obra/test-slug/capitulo-1",
                }
            ],
            "forceTranslate": True,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/scraper/start", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["count"] == 1

        mock_session.commit.assert_awaited_once()
        mock_redis.enqueue_job.assert_awaited_once_with(
            "scrape_and_download_chapter",
            "lycantoons",
            "ch-1",
            "https://lycantoons.com/obra/test-slug/capitulo-1",
            True,
            _job_id="scrape_ch-1",
        )


@pytest.mark.asyncio
async def test_retry_scraped_chapter_success():
    from src.db.models import Chapter, TranslationStatus

    chapter_record = Chapter(
        id="lycantoons:mock-slug:2",
        manga_id="lycantoons:mock-slug",
        chapter_number="2",
        status=TranslationStatus.ERROR,
    )

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = chapter_record
    mock_session.execute = AsyncMock(return_value=mock_res)

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_redis = AsyncMock()

    with patch("src.main.get_registry") as mock_get_registry, \
         patch("src.main.AsyncSessionLocal", return_value=MockSessionContext()), \
         patch("src.main.redis_pool", mock_redis):

        mock_provider = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_provider.return_value = mock_provider
        mock_get_registry.return_value = mock_registry

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/manga/lycantoons:mock-slug:2/retry")
            assert response.status_code == 200
            assert response.json() == {"status": "retrying"}

        assert chapter_record.status == TranslationStatus.PROCESSING
        mock_redis.delete.assert_awaited_once_with(
            "arq:result:scrape_lycantoons:mock-slug:2",
            "arq:job:scrape_lycantoons:mock-slug:2",
            "arq:in-progress:scrape_lycantoons:mock-slug:2",
        )
        mock_redis.zrem.assert_awaited_once_with("arq:queue", "scrape_lycantoons:mock-slug:2")
        mock_redis.enqueue_job.assert_awaited_once_with(
            "scrape_and_download_chapter",
            "lycantoons",
            "lycantoons:mock-slug:2",
            "https://lycantoons.com/series/mock-slug/2",
            False,
            _job_id="scrape_lycantoons:mock-slug:2",
        )

