import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.scrapers.providers.valirscans import ValirScansProvider


def test_valirscans_can_handle():
    provider = ValirScansProvider()
    assert provider.can_handle("https://valirscans.org/series/comic/the-counts-secret-maid?page=2")
    assert provider.can_handle("https://valirscans.org/series/comic/another-series")
    assert provider.can_handle("https://valirscans.org/series/novel/some-novel")
    assert not provider.can_handle("https://lycantoons.com/manga/test")
    assert not provider.can_handle("https://mangadex.org/title/1234")


def test_valirscans_extract_slug():
    provider = ValirScansProvider()
    slug = provider._extract_slug("https://valirscans.org/series/comic/the-counts-secret-maid?page=2")
    assert slug == "the-counts-secret-maid"


@pytest.mark.asyncio
async def test_valirscans_extract_manga_info_pagination():
    provider = ValirScansProvider()

    page1_html = """
    <html>
      <head><title>The Count's Secret Maid - Valir Scans</title></head>
      <body>
        <h1 class="text-xl">The Count's Secret Maid</h1>
        <img class="cover" src="https://valirscans.org/uploads/series/cover.webp" />
        <a href="/series/comic/the-counts-secret-maid?page=2">Next</a>
        <a href="/series/comic/the-counts-secret-maid/chapter/1">Chapter 1</a>
        <a href="/series/comic/the-counts-secret-maid/chapter/2">Chapter 2</a>
      </body>
    </html>
    """

    page2_html = """
    <html>
      <body>
        <a href="/series/comic/the-counts-secret-maid/chapter/3">Chapter 3</a>
      </body>
    </html>
    """

    async def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        if "page=2" in str(url):
            mock_resp.text = page2_html
        else:
            mock_resp.text = page1_html
        return mock_resp

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=mock_get)):
        preview = await provider.extract_manga_info("https://valirscans.org/series/comic/the-counts-secret-maid?page=2")

    assert preview.provider == "valirscans"
    assert preview.manga_id == "valirscans:the-counts-secret-maid"
    assert preview.title == "The Count's Secret Maid"
    assert preview.cover_url == "https://valirscans.org/uploads/series/cover.webp"
    assert len(preview.chapters) == 3
    assert preview.chapters[0].number == "1"
    assert preview.chapters[2].number == "3"
    assert preview.chapters[2].id == "valirscans:the-counts-secret-maid:3"


@pytest.mark.asyncio
async def test_valirscans_extract_chapter_pages():
    provider = ValirScansProvider()
    chapter_html = """
    <html>
      <body>
        <script>window.__DATA__ = []</script>
        <img src="https://media.valirscans.org/series/the-counts-secret-maid/0101/p-1.webp" />
        <img src="https://media.valirscans.org/series/the-counts-secret-maid/0101/p-2.webp" />
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = chapter_html

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        pages = await provider.extract_chapter_pages("https://valirscans.org/series/comic/the-counts-secret-maid/chapter/101")

    assert len(pages) == 2
    assert pages[0].page_index == 1
    assert pages[0].image_url == "https://media.valirscans.org/series/the-counts-secret-maid/0101/p-1.webp"
    assert pages[1].page_index == 2


@pytest.mark.asyncio
async def test_valirscans_download_page_image():
    provider = ValirScansProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"fake-image-bytes"

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        content = await provider.download_page_image("https://media.valirscans.org/series/the-counts-secret-maid/0101/p-1.webp")

    assert content == b"fake-image-bytes"


def test_valirscans_registered_in_registry():
    from src.scrapers.registry import get_registry

    registry = get_registry()
    provider = registry.get_provider("valirscans")
    assert provider is not None
    assert isinstance(provider, ValirScansProvider)

    matched = registry.get_provider_for_url("https://valirscans.org/series/comic/the-counts-secret-maid")
    assert matched is provider

