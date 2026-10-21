import pytest
from src.scrapers.providers.lycantoons import LycantoonsProvider


def test_lycantoons_can_handle_valid_urls():
    provider = LycantoonsProvider()
    assert provider.can_handle("https://lycantoons.com/series/a-empregada-secreta-do-conde") is True
    assert provider.can_handle("http://lycantoons.com/series/qualquer-obra") is True
    assert provider.can_handle("https://mangadex.org/title/12345") is False
    assert provider.can_handle("https://google.com") is False


def test_lycantoons_extracts_slug():
    provider = LycantoonsProvider()
    slug = provider._extract_slug("https://lycantoons.com/series/a-empregada-secreta-do-conde")
    assert slug == "a-empregada-secreta-do-conde"

    slug2 = provider._extract_slug("https://lycantoons.com/series/a-empregada-secreta-do-conde/10")
    assert slug2 == "a-empregada-secreta-do-conde"


def test_lycantoons_parse_rsc_payload():
    provider = LycantoonsProvider()
    sample_html = '''
    <script>self.__next_f.push([1,"\\"title\\":\\"A Empregada Secreta do Conde\\",\\"capitulos\\":[{\\"id\\":1001,\\"numero\\":2},{\\"id\\":1000,\\"numero\\":1}]"])</script>
    '''
    info = provider._parse_series_data_from_html(sample_html, "a-empregada-secreta-do-conde")
    assert info["title"] == "A Empregada Secreta do Conde"
    assert len(info["chapters"]) == 2
    assert info["chapters"][0]["number"] == "1"
    assert info["chapters"][1]["number"] == "2"


@pytest.mark.asyncio
async def test_lycantoons_download_pages(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from src.scrapers.base import PageItem

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.body = AsyncMock(return_value=b"fake-bytes")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_resp)

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

    monkeypatch.setattr("src.scrapers.providers.lycantoons.async_playwright", lambda: MockAsyncPlaywright())

    provider = LycantoonsProvider()
    pages = [PageItem(page_index=0, image_url="https://cdn.lycantoons.com/p0.jpg")]
    downloaded = []
    async for p, body in provider.download_pages(pages):
        downloaded.append((p.page_index, body))

    assert len(downloaded) == 1
    assert downloaded[0] == (0, b"fake-bytes")
    mock_browser.close.assert_awaited_once()
