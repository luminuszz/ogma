import pytest
from src.mangadex import fetch_manga_feed, fetch_chapter_pages

@pytest.mark.asyncio
async def test_fetch_manga_feed():
    # Uses a known manga ID (e.g., Solo Leveling or similar)
    feed = await fetch_manga_feed("c52b2ce3-7f95-469c-96b0-479524fc7a1a")
    assert isinstance(feed, list)
    if len(feed) > 0:
        assert "id" in feed[0]
        assert "chapter" in feed[0]

@pytest.mark.asyncio
async def test_fetch_chapter_pages():
    pages = await fetch_chapter_pages("0aaf8b27-0013-4ae0-8935-91a089466874")
    assert isinstance(pages, list)
