from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.db.models import Chapter, Manga
from src.main import app
from src.scrapers.base import ChapterItem, MangaPreview


class MockSessionContext:
    def __init__(self):
        self.session = AsyncMock()
        self.mangas = []
        self.chapters = []

        def mock_add(obj):
            if isinstance(obj, Manga):
                self.mangas.append(obj)
            elif isinstance(obj, Chapter):
                self.chapters.append(obj)

        def mock_add_all(objs):
            for obj in objs:
                mock_add(obj)

        async def mock_execute(stmt):
            mock_res = MagicMock()
            stmt_str = str(stmt).lower()
            if "chapter" in stmt_str and "manga_id" in stmt_str and "mangas" not in stmt_str:
                mock_res.all.return_value = [
                    (ch.manga_id, ch.chapter_number) for ch in self.chapters
                ]
            else:
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = self.mangas
                mock_res.scalars.return_value = scalars_mock
                mock_res.all.return_value = self.mangas
            return mock_res

        self.session.add = MagicMock(side_effect=mock_add)
        self.session.add_all = MagicMock(side_effect=mock_add_all)
        self.session.commit = AsyncMock()
        self.session.execute = AsyncMock(side_effect=mock_execute)

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_preview_returns_existing_works_and_suggestion():
    existing_manga = Manga(id="lycantoons:a-empregada-secreta-do-conde", title="A Empregada Secreta do Conde")
    ch1 = Chapter(id="lycantoons:a-empregada-secreta-do-conde:1", manga_id=existing_manga.id, chapter_number="1")
    ch2 = Chapter(id="lycantoons:a-empregada-secreta-do-conde:2", manga_id=existing_manga.id, chapter_number="2")

    mock_db = MockSessionContext()
    mock_db.mangas = [existing_manga]
    mock_db.chapters = [ch1, ch2]

    mock_preview = MangaPreview(
        provider="valirscans",
        manga_id="valirscans:the-counts-secret-maid",
        title="The Count's Secret Maid",
        cover_url="https://valirscans.org/cover.webp",
        chapters=[
            ChapterItem(id="valirscans:the-counts-secret-maid:1", number="1", url="https://valirscans.org/ch1"),
            ChapterItem(id="valirscans:the-counts-secret-maid:2", number="2", url="https://valirscans.org/ch2"),
            ChapterItem(id="valirscans:the-counts-secret-maid:3", number="3", url="https://valirscans.org/ch3"),
        ],
    )

    transport = ASGITransport(app=app)
    with patch("src.scrapers.providers.valirscans.ValirScansProvider.extract_manga_info", new=AsyncMock(return_value=mock_preview)), \
         patch("src.main.AsyncSessionLocal", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/scraper/preview", json={"url": "https://valirscans.org/series/comic/the-counts-secret-maid"})

    assert resp.status_code == 200
    data = resp.json()
    assert "existingWorks" in data
    assert "suggestedMangaId" in data
    assert len(data["existingWorks"]) >= 1

    matched = next((m for m in data["existingWorks"] if m["id"] == "lycantoons:a-empregada-secreta-do-conde"), None)
    assert matched is not None
    assert set(matched["existingChapterNumbers"]) == {"1", "2"}
    assert data["suggestedMangaId"] == "lycantoons:a-empregada-secreta-do-conde"

from src.main import ExistingMangaSummary, find_suggested_manga_id


def test_find_suggested_manga_id_exact_and_close_matches():
    summaries = [
        ExistingMangaSummary(id="m1", title="Solo Leveling", existingChapterNumbers=["1", "2"]),
        ExistingMangaSummary(id="m2", title="A Empregada Secreta do Conde", existingChapterNumbers=["1"]),
    ]
    # Exact match
    assert find_suggested_manga_id("Solo Leveling", summaries) == "m1"
    # Case insensitive and punctuation
    assert find_suggested_manga_id("solo-leveling!", summaries) == "m1"
    # Semantic/lexical similarity
    assert find_suggested_manga_id("The Count's Secret Maid", summaries) == "m2"


def test_find_suggested_manga_id_no_match():
    summaries = [
        ExistingMangaSummary(id="m1", title="One Piece", existingChapterNumbers=["1"]),
    ]
    assert find_suggested_manga_id("Completely Unrelated Manga 123", summaries) is None
    assert find_suggested_manga_id("", summaries) is None
    assert find_suggested_manga_id("Solo Leveling", []) is None


@pytest.mark.asyncio
async def test_preview_with_empty_library():
    mock_db = MockSessionContext()
    mock_db.mangas = []
    mock_db.chapters = []

    mock_preview = MangaPreview(
        provider="valirscans",
        manga_id="valirscans:new-title",
        title="New Title",
        cover_url=None,
        chapters=[],
    )

    transport = ASGITransport(app=app)
    with patch("src.scrapers.providers.valirscans.ValirScansProvider.extract_manga_info", new=AsyncMock(return_value=mock_preview)), \
         patch("src.main.AsyncSessionLocal", return_value=mock_db):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/scraper/preview", json={"url": "https://valirscans.org/series/comic/new-title"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["existingWorks"] == []
    assert data["suggestedMangaId"] is None
