import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.db.models import Chapter, Page, TranslationStatus
from src.scrapers.base import PageItem
from src.worker import WorkerSettings, scrape_and_download_chapter


def test_worker_settings_registers_scraper_job():
    func_names = [f.__name__ for f in WorkerSettings.functions]
    assert "scrape_and_download_chapter" in func_names


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_provider_not_found():
    with patch("src.worker.get_registry") as mock_get_reg:
        mock_reg = MagicMock()
        mock_reg.get_provider.return_value = None
        mock_get_reg.return_value = mock_reg

        with pytest.raises(ValueError, match="Provider nonexistent not found."):
            await scrape_and_download_chapter(
                ctx={},
                provider_name="nonexistent",
                chapter_id="ch-1",
                chapter_url="https://test.com/chapter-1",
            )


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_success():
    # 1. Setup mock provider
    mock_provider = MagicMock()
    mock_provider.name = "test_provider"
    mock_provider.extract_chapter_pages = AsyncMock(
        return_value=[
            PageItem(page_index=1, image_url="https://img.test/p1.png"),
            PageItem(page_index=2, image_url="https://img.test/p2.png"),
        ]
    )

    async def mock_download_pages(pages):
        for p in pages:
            yield p, b"fake-image-bytes"

    mock_provider.download_pages = mock_download_pages

    mock_reg = MagicMock()
    mock_reg.get_provider.return_value = mock_provider

    # 2. Setup mock DB session
    chapter_record = Chapter(id="ch-1", total_pages=0, status=TranslationStatus.PENDING)
    page_1_record = Page(chapter_id="ch-1", page_index=1, status=TranslationStatus.PENDING)
    page_2_record = None  # to test creation of new Page

    mock_session = AsyncMock()
    added_objects = []
    mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    # We will simulate multiple queries to session.execute:
    # 1) Chapter lookup (before page loop): returns chapter_record
    # 2) Page 1 lookup (in prepare loop): returns page_1_record
    # 3) Page 2 lookup (in prepare loop): returns None (triggers session.add)
    # 4) Page 1 lookup (after upload): returns page_1_record
    # 5) Page 2 lookup (after upload): returns the newly added page_2
    # 6) Chapter lookup (at end): returns chapter_record
    def make_scalar_res(val):
        res = MagicMock()
        res.scalar_one_or_none.return_value = val
        return res

    def get_page_2():
        for obj in added_objects:
            if isinstance(obj, Page) and obj.page_index == 2:
                return obj
        return None

    execute_call_count = 0

    async def mock_execute(statement, *args, **kwargs):
        nonlocal execute_call_count
        execute_call_count += 1
        if execute_call_count == 1:
            return make_scalar_res(chapter_record)
        elif execute_call_count == 2:
            return make_scalar_res(page_1_record)
        elif execute_call_count == 3:
            return make_scalar_res(page_2_record)
        elif execute_call_count == 4:
            return make_scalar_res(page_1_record)
        elif execute_call_count == 5:
            return make_scalar_res(get_page_2())
        elif execute_call_count == 6:
            return make_scalar_res(chapter_record)
        return make_scalar_res(None)

    mock_session.execute = AsyncMock(side_effect=mock_execute)

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # 3. Setup mock httpx client
    mock_http_response = MagicMock()
    mock_http_response.content = b"fake-image-bytes"
    mock_http_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_http_response)

    class MockHttpClientContext:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_http_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # 4. Setup mock redis
    mock_redis = AsyncMock()

    with patch("src.worker.get_registry", return_value=mock_reg), \
         patch("src.worker.AsyncSessionLocal", return_value=MockSessionContext()), \
         patch("src.worker.upload_image_to_r2", new_callable=AsyncMock) as mock_upload, \
         patch("src.worker.redis.from_url", new_callable=AsyncMock) as mock_from_url:

        mock_upload.side_effect = lambda bytes_data, dest: f"https://r2.test/{dest}"
        mock_from_url.return_value = mock_redis

        await scrape_and_download_chapter(
            ctx={},
            provider_name="test_provider",
            chapter_id="ch-1",
            chapter_url="https://test.com/ch-1",
        )

        # Assertions
        mock_provider.extract_chapter_pages.assert_awaited_once_with("https://test.com/ch-1")
        assert chapter_record.total_pages == 2
        assert chapter_record.status == TranslationStatus.DONE

        # Check page 1
        assert page_1_record.status == TranslationStatus.DONE
        assert page_1_record.image_url == "https://r2.test/ch-1/1.png"

        # Check page 2
        page_2 = get_page_2()
        assert page_2 is not None
        assert page_2.status == TranslationStatus.DONE
        assert page_2.image_url == "https://r2.test/ch-1/2.png"

        # Check redis publishes
        assert mock_redis.publish.call_count == 2
        mock_redis.publish.assert_any_call(
            "chapter:ch-1",
            json.dumps({"page_index": 1, "url": "https://r2.test/ch-1/1.png"}),
        )
        mock_redis.publish.assert_any_call(
            "chapter:ch-1",
            json.dumps({"page_index": 2, "url": "https://r2.test/ch-1/2.png"}),
        )
        mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_page_error():
    mock_provider = MagicMock()
    mock_provider.name = "test_provider"
    mock_provider.extract_chapter_pages = AsyncMock(
        return_value=[
            PageItem(page_index=1, image_url="https://img.test/p1.png"),
        ]
    )

    async def mock_download_pages_error(pages):
        for p in pages:
            yield p, b"fake-image-bytes"

    mock_provider.download_pages = mock_download_pages_error

    mock_reg = MagicMock()
    mock_reg.get_provider.return_value = mock_provider

    chapter_record = Chapter(id="ch-error", total_pages=0, status=TranslationStatus.PENDING)
    page_record = Page(chapter_id="ch-error", page_index=1, status=TranslationStatus.PENDING)

    mock_session = AsyncMock()

    def make_scalar_res(val):
        res = MagicMock()
        res.scalar_one_or_none.return_value = val
        return res

    execute_call_count = 0

    async def mock_execute(statement, *args, **kwargs):
        nonlocal execute_call_count
        execute_call_count += 1
        if execute_call_count == 1:
            return make_scalar_res(chapter_record)
        elif execute_call_count in (2, 3):
            return make_scalar_res(page_record)
        elif execute_call_count == 4:
            return make_scalar_res(chapter_record)
        return make_scalar_res(None)

    mock_session.execute = AsyncMock(side_effect=mock_execute)

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_redis = AsyncMock()

    with patch("src.worker.get_registry", return_value=mock_reg), \
         patch("src.worker.AsyncSessionLocal", return_value=MockSessionContext()), \
         patch("src.worker.upload_image_to_r2", new_callable=AsyncMock) as mock_upload, \
         patch("src.worker.redis.from_url", new_callable=AsyncMock) as mock_from_url:

        mock_upload.side_effect = RuntimeError("Upload error")
        mock_from_url.return_value = mock_redis

        await scrape_and_download_chapter(
            ctx={},
            provider_name="test_provider",
            chapter_id="ch-error",
            chapter_url="https://test.com/ch-error",
        )

        mock_upload.assert_awaited_once()
        assert page_record.status == TranslationStatus.ERROR
        assert chapter_record.status == TranslationStatus.ERROR
        mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_extraction_error():
    mock_provider = MagicMock()
    mock_provider.name = "test_provider"
    mock_provider.extract_chapter_pages = AsyncMock(side_effect=RuntimeError("Extraction crashed"))

    mock_reg = MagicMock()
    mock_reg.get_provider.return_value = mock_provider

    chapter_record = Chapter(id="ch-fail", total_pages=0, status=TranslationStatus.PENDING)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=chapter_record)))

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.worker.get_registry", return_value=mock_reg), \
         patch("src.worker.AsyncSessionLocal", return_value=MockSessionContext()):
        with pytest.raises(RuntimeError, match="Extraction crashed"):
            await scrape_and_download_chapter(
                ctx={},
                provider_name="test_provider",
                chapter_id="ch-fail",
                chapter_url="https://test.com/ch-fail",
            )

        assert chapter_record.status == TranslationStatus.ERROR
        mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_empty_pages_error():
    mock_provider = MagicMock()
    mock_provider.name = "test_provider"
    mock_provider.extract_chapter_pages = AsyncMock(return_value=[])

    mock_reg = MagicMock()
    mock_reg.get_provider.return_value = mock_provider

    chapter_record = Chapter(id="ch-empty", total_pages=0, status=TranslationStatus.PENDING)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=chapter_record)))

    class MockSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("src.worker.get_registry", return_value=mock_reg), \
         patch("src.worker.AsyncSessionLocal", return_value=MockSessionContext()):
        with pytest.raises(ValueError, match="No pages extracted"):
            await scrape_and_download_chapter(
                ctx={},
                provider_name="test_provider",
                chapter_id="ch-empty",
                chapter_url="https://test.com/ch-empty",
            )

        assert chapter_record.status == TranslationStatus.ERROR
        mock_session.commit.assert_awaited()

