from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.scrapers.base import PageItem
from src.worker import scrape_and_download_chapter, translate_page_image


class MockSessionContext:
    def __init__(self):
        self.session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        self.session.execute = AsyncMock(return_value=mock_result)
        self.session.commit = AsyncMock()
        self.session.add = MagicMock()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_calls_translate_when_force_translate_true():
    chapter_id = "valirscans:the-counts-secret-maid:101"
    mock_pages = [PageItem(page_index=1, image_url="https://media.valirscans.org/p1.webp")]

    async def mock_download_pages(pages):
        for p in pages:
            yield p, b"original-image-bytes"

    mock_provider = MagicMock()
    mock_provider.extract_chapter_pages = AsyncMock(return_value=mock_pages)
    mock_provider.download_pages = mock_download_pages

    mock_reg_inst = MagicMock()
    mock_reg_inst.get_provider.return_value = mock_provider

    with patch("src.worker.get_registry", return_value=mock_reg_inst), \
         patch("src.worker.AsyncSessionLocal", side_effect=MockSessionContext), \
         patch("src.worker.translate_page_image", new=AsyncMock(return_value=b"translated-image-bytes")) as mock_trans, \
         patch("src.worker.upload_image_to_r2", new=AsyncMock(return_value="https://r2/dest.png")) as mock_upload, \
         patch("src.worker.redis.from_url", new=AsyncMock(return_value=AsyncMock())):

        await scrape_and_download_chapter(
            ctx={},
            provider_name="valirscans",
            chapter_id=chapter_id,
            chapter_url="https://valirscans.org/ch101",
            force_translate=True,
        )

    # Assert translate_page_image was invoked with original bytes
    mock_trans.assert_called_once_with(b"original-image-bytes", source_lang="ENG")
    # Assert upload_image_to_r2 received translated bytes
    mock_upload.assert_called_once_with(b"translated-image-bytes", f"{chapter_id}/1.png")


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_falls_back_to_original_when_translation_fails():
    chapter_id = "valirscans:the-counts-secret-maid:101"
    mock_pages = [PageItem(page_index=1, image_url="https://media.valirscans.org/p1.webp")]

    async def mock_download_pages(pages):
        for p in pages:
            yield p, b"original-image-bytes"

    mock_provider = MagicMock()
    mock_provider.extract_chapter_pages = AsyncMock(return_value=mock_pages)
    mock_provider.download_pages = mock_download_pages

    mock_reg_inst = MagicMock()
    mock_reg_inst.get_provider.return_value = mock_provider

    with patch("src.worker.get_registry", return_value=mock_reg_inst), \
         patch("src.worker.AsyncSessionLocal", side_effect=MockSessionContext), \
         patch("src.worker.translate_page_image", new=AsyncMock(side_effect=RuntimeError("ML engine timeout"))) as mock_trans, \
         patch("src.worker.upload_image_to_r2", new=AsyncMock(return_value="https://r2/dest.png")) as mock_upload, \
         patch("src.worker.redis.from_url", new=AsyncMock(return_value=AsyncMock())):

        await scrape_and_download_chapter(
            ctx={},
            provider_name="valirscans",
            chapter_id=chapter_id,
            chapter_url="https://valirscans.org/ch101",
            force_translate=True,
        )

    # Assert translate_page_image was called
    mock_trans.assert_called_once_with(b"original-image-bytes", source_lang="ENG")
    # Assert upload_image_to_r2 fell back to original bytes despite translation error
    mock_upload.assert_called_once_with(b"original-image-bytes", f"{chapter_id}/1.png")


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_does_not_call_translate_when_force_translate_false():
    chapter_id = "valirscans:the-counts-secret-maid:101"
    mock_pages = [PageItem(page_index=1, image_url="https://media.valirscans.org/p1.webp")]

    async def mock_download_pages(pages):
        for p in pages:
            yield p, b"original-image-bytes"

    mock_provider = MagicMock()
    mock_provider.extract_chapter_pages = AsyncMock(return_value=mock_pages)
    mock_provider.download_pages = mock_download_pages

    mock_reg_inst = MagicMock()
    mock_reg_inst.get_provider.return_value = mock_provider

    with patch("src.worker.get_registry", return_value=mock_reg_inst), \
         patch("src.worker.AsyncSessionLocal", side_effect=MockSessionContext), \
         patch("src.worker.translate_page_image", new=AsyncMock()) as mock_trans, \
         patch("src.worker.upload_image_to_r2", new=AsyncMock(return_value="https://r2/dest.png")) as mock_upload, \
         patch("src.worker.redis.from_url", new=AsyncMock(return_value=AsyncMock())):

        await scrape_and_download_chapter(
            ctx={},
            provider_name="valirscans",
            chapter_id=chapter_id,
            chapter_url="https://valirscans.org/ch101",
            force_translate=False,
        )

    # Assert translate_page_image was NOT called
    mock_trans.assert_not_called()
    # Assert upload_image_to_r2 received original bytes
    mock_upload.assert_called_once_with(b"original-image-bytes", f"{chapter_id}/1.png")


@pytest.mark.asyncio
async def test_translate_page_image_calls_ml_service():
    mock_resp = MagicMock()
    mock_resp.content = b"translated-bytes"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    class MockClientContext:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()):
        res = await translate_page_image(b"original-bytes", source_lang="ENG")

    assert res == b"translated-bytes"
    mock_client.post.assert_called_once()
    call_args, call_kwargs = mock_client.post.call_args
    assert "/translate/with-form/image" in call_args[0]
    assert "image" in call_kwargs["files"]
    assert "config" in call_kwargs["data"]
