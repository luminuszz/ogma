from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.db.models import Chapter, Manga, TranslationStatus
from src.main import app


class MockSessionContext:
    def __init__(self, mangas=None, chapters=None):
        self.session = AsyncMock()
        self.mangas = {m.id: m for m in (mangas or [])}
        self.chapters = {c.id: c for c in (chapters or [])}

        def mock_add(obj):
            if isinstance(obj, Manga):
                self.mangas[obj.id] = obj
            elif isinstance(obj, Chapter):
                self.chapters[obj.id] = obj

        async def mock_execute(stmt):
            mock_res = MagicMock()
            entity = None
            if hasattr(stmt, "column_descriptions") and stmt.column_descriptions:
                entity = stmt.column_descriptions[0].get("entity")

            compiled = stmt.compile()
            binds = compiled.params
            target_id = list(binds.values())[0] if binds else None

            if entity is Manga or "mangas" in str(stmt).lower():
                found = self.mangas.get(target_id)
                mock_res.scalar_one_or_none.return_value = found
                mock_res.scalar_one.return_value = found
            elif entity is Chapter or "chapters" in str(stmt).lower():
                found = self.chapters.get(target_id)
                mock_res.scalar_one_or_none.return_value = found
                mock_res.scalar_one.return_value = found
            return mock_res

        self.session.add = MagicMock(side_effect=mock_add)
        self.session.commit = AsyncMock()
        self.session.execute = AsyncMock(side_effect=mock_execute)

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_scraper_start_links_to_existing_manga_without_overwriting_title():
    existing_manga = Manga(
        id="lycantoons:a-empregada-secreta-do-conde",
        title="A Empregada Secreta do Conde",
    )
    mock_db = MockSessionContext(mangas=[existing_manga])

    payload = {
        "provider": "valirscans",
        "mangaId": "lycantoons:a-empregada-secreta-do-conde",
        "title": "The Count's Secret Maid",  # Foreign title from Valir Scans
        "forceTranslate": True,
        "chapters": [
            {
                "id": "valirscans:the-counts-secret-maid:101",
                "number": "101",
                "title": "Capítulo 101",
                "url": "https://valirscans.org/ch101",
            }
        ],
    }

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()
    mock_redis.delete = AsyncMock()

    transport = ASGITransport(app=app)
    with patch("src.main.AsyncSessionLocal", return_value=mock_db), \
         patch("src.main.redis_pool", mock_redis):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/scraper/start", json=payload)

    assert resp.status_code == 200
    assert resp.json() == {"status": "queued", "count": 1}

    # Verify Manga title was NOT overwritten
    manga_in_db = mock_db.mangas["lycantoons:a-empregada-secreta-do-conde"]
    assert manga_in_db.title == "A Empregada Secreta do Conde"

    # Verify Chapter was created linked to target mangaId
    assert "valirscans:the-counts-secret-maid:101" in mock_db.chapters
    chapter = mock_db.chapters["valirscans:the-counts-secret-maid:101"]
    assert chapter.manga_id == "lycantoons:a-empregada-secreta-do-conde"
    assert chapter.chapter_number == "101"
    assert chapter.status == TranslationStatus.PROCESSING

    # Verify ARQ was called with forceTranslate=True
    mock_redis.enqueue_job.assert_awaited_once_with(
        "scrape_and_download_chapter",
        "valirscans",
        "valirscans:the-counts-secret-maid:101",
        "https://valirscans.org/ch101",
        True,
        _job_id="scrape_valirscans:the-counts-secret-maid:101",
    )


@pytest.mark.asyncio
async def test_scraper_start_creates_new_manga_when_not_existing():
    mock_db = MockSessionContext()

    payload = {
        "provider": "valirscans",
        "mangaId": "valirscans:new-title",
        "title": "New Title",
        "forceTranslate": False,
        "chapters": [
            {
                "id": "valirscans:new-title:1",
                "number": "1",
                "url": "https://valirscans.org/ch1",
            }
        ],
    }

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()
    mock_redis.delete = AsyncMock()

    transport = ASGITransport(app=app)
    with patch("src.main.AsyncSessionLocal", return_value=mock_db), \
         patch("src.main.redis_pool", mock_redis):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/scraper/start", json=payload)

    assert resp.status_code == 200
    assert "valirscans:new-title" in mock_db.mangas
    assert mock_db.mangas["valirscans:new-title"].title == "New Title"
    assert "valirscans:new-title:1" in mock_db.chapters
    assert mock_db.chapters["valirscans:new-title:1"].manga_id == "valirscans:new-title"


@pytest.mark.asyncio
async def test_scraper_start_updates_existing_chapter_association():
    existing_manga = Manga(id="manga:target", title="Target Manga")
    existing_chapter = Chapter(
        id="valirscans:chapter:1",
        manga_id="manga:old",
        chapter_number="1",
        status=TranslationStatus.ERROR,
    )
    mock_db = MockSessionContext(mangas=[existing_manga], chapters=[existing_chapter])

    payload = {
        "provider": "valirscans",
        "mangaId": "manga:target",
        "title": "Ignored Title",
        "forceTranslate": False,
        "chapters": [
            {
                "id": "valirscans:chapter:1",
                "number": "1",
                "url": "https://valirscans.org/ch1",
            }
        ],
    }

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()
    mock_redis.delete = AsyncMock()

    transport = ASGITransport(app=app)
    with patch("src.main.AsyncSessionLocal", return_value=mock_db), \
         patch("src.main.redis_pool", mock_redis):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/scraper/start", json=payload)

    assert resp.status_code == 200
    assert existing_chapter.manga_id == "manga:target"
    assert existing_chapter.status == TranslationStatus.PROCESSING
