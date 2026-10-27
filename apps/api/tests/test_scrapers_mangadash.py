import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.scrapers.base import PageItem
from src.scrapers.providers.mangadash import MangadashProvider
from src.scrapers.registry import get_registry


def test_mangadash_can_handle():
    provider = MangadashProvider()
    assert provider.can_handle("https://mangadash.net/manga/40-dandadan")
    assert provider.can_handle("https://mangadash.net/manga/40-dandadan/")
    assert provider.can_handle("https://mangadash.net/capitulo/40-dandadan/1")
    assert provider.can_handle("http://www.mangadash.net/manga/421-beware-the-villainess")
    assert not provider.can_handle("https://lycantoons.com/series/test")
    assert not provider.can_handle("https://valirscans.org/series/comic/test")
    assert not provider.can_handle("https://mangadex.org/title/1234")


def test_mangadash_extract_slug():
    provider = MangadashProvider()
    assert provider._extract_slug("https://mangadash.net/manga/40-dandadan") == "40-dandadan"
    assert provider._extract_slug("https://mangadash.net/manga/40-dandadan/") == "40-dandadan"
    assert provider._extract_slug("https://mangadash.net/capitulo/40-dandadan/1") == "40-dandadan"
    assert provider._extract_slug("https://mangadash.net/other/path") == ""


@pytest.mark.asyncio
async def test_mangadash_extract_manga_info():
    provider = MangadashProvider()

    sample_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta property="og:title" content="Dandadan - Ler Online Grátis | MangáDash">
        <meta property="og:image" content="https://s4.anilist.co/cover.jpg">
    </head>
    <body>
        <h1 class="neon-title">Dandadan</h1>
        <div class="chapters-scroll-container">
            <a href="/capitulo/40-dandadan/2" class="chapter-row" data-chapter-number="2">
                <div class="chapter-title-group"><h4>Capítulo 2</h4></div>
            </a>
            <a href="/capitulo/40-dandadan/1" class="chapter-row" data-chapter-number="1">
                <div class="chapter-title-group"><h4>Capítulo 1</h4></div>
            </a>
            <a href="/capitulo/40-dandadan/1.5" class="chapter-row" data-chapter-number="1.5">
                <div class="chapter-title-group"><h4>Capítulo 1.5</h4></div>
            </a>
        </div>
    </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.text = sample_html
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        preview = await provider.extract_manga_info("https://mangadash.net/manga/40-dandadan")

    assert preview.provider == "mangadash"
    assert preview.manga_id == "mangadash:40-dandadan"
    assert preview.title == "Dandadan"
    assert preview.cover_url == "https://s4.anilist.co/cover.jpg"
    assert len(preview.chapters) == 3
    # Sorted numerically: 1, 1.5, 2
    assert preview.chapters[0].number == "1"
    assert preview.chapters[0].id == "mangadash:40-dandadan:1"
    assert preview.chapters[0].url == "https://mangadash.net/capitulo/40-dandadan/1"
    assert preview.chapters[1].number == "1.5"
    assert preview.chapters[2].number == "2"


@pytest.mark.asyncio
async def test_mangadash_extract_chapter_pages(monkeypatch):
    mock_page = AsyncMock()
    mock_page.route = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=12)

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    class MockAsyncPlaywright:
        async def __aenter__(self):
            return mock_playwright

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(
        "src.scrapers.providers.mangadash.async_playwright",
        lambda: MockAsyncPlaywright(),
    )

    provider = MangadashProvider()
    pages = await provider.extract_chapter_pages("https://mangadash.net/capitulo/40-dandadan/1")

    assert len(pages) == 12
    assert pages[0].page_index == 0
    assert pages[0].image_url == "https://mangadash.net/capitulo/40-dandadan/1#page=1"
    assert pages[11].page_index == 11
    assert pages[11].image_url == "https://mangadash.net/capitulo/40-dandadan/1#page=12"
    mock_browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_mangadash_download_pages(monkeypatch):
    dummy_png = b"\x89PNG\r\n\x1a\nfake-png-bytes"
    data_url = f"data:image/png;base64,{base64.b64encode(dummy_png).decode()}"

    mock_page = AsyncMock()
    mock_page.route = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=data_url)

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    class MockAsyncPlaywright:
        async def __aenter__(self):
            return mock_playwright

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(
        "src.scrapers.providers.mangadash.async_playwright",
        lambda: MockAsyncPlaywright(),
    )

    provider = MangadashProvider()
    pages = [
        PageItem(page_index=0, image_url="https://mangadash.net/capitulo/40-dandadan/1#page=1"),
        PageItem(page_index=1, image_url="https://mangadash.net/capitulo/40-dandadan/1#page=2"),
    ]

    downloaded = []
    async for p_item, b_data in provider.download_pages(pages):
        downloaded.append((p_item.page_index, b_data))

    assert len(downloaded) == 2
    assert downloaded[0] == (0, dummy_png)
    assert downloaded[1] == (1, dummy_png)
    mock_browser.close.assert_awaited_once()


def test_mangadash_registry():
    registry = get_registry()
    provider = registry.get_provider("mangadash")
    assert provider is not None
    assert provider.name == "mangadash"

    found = registry.get_provider_for_url("https://mangadash.net/manga/40-dandadan")
    assert found is not None
    assert found.name == "mangadash"
