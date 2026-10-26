import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from src.db.models import Chapter, Page, TranslationStatus
from src.scrapers.base import PageItem
from src.worker import (
    WorkerSettings,
    scrape_and_download_chapter,
    startup,
    translate_page_image,
    warmup_manga_translator,
)


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
    sent_config = json.loads(call_kwargs["data"]["config"])
    assert sent_config["inpainter"] == {"inpainter": "lama_mpe"}
    assert sent_config["detector"] == {
        "unclip_ratio": 2.4,
        "box_threshold": 0.6,
        "text_threshold": 0.2,
    }


@pytest.mark.asyncio
async def test_translate_page_image_retries_and_succeeds():
    mock_resp = MagicMock()
    mock_resp.content = b"translated-on-retry"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[
            RuntimeError("Network flap 1"),
            RuntimeError("Network flap 2"),
            mock_resp,
        ]
    )

    class MockClientContext:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()), \
         patch("src.worker.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        res = await translate_page_image(b"original-bytes", source_lang="ENG")

    assert res == b"translated-on-retry"
    assert mock_client.post.call_count == 3
    assert mock_sleep.call_args_list == [call(2), call(4)]


@pytest.mark.asyncio
async def test_translate_page_image_fails_after_max_retries():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=RuntimeError("Persistent 500 error"))

    class MockClientContext:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()), \
         patch("src.worker.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        with pytest.raises(RuntimeError, match="Persistent 500 error"):
            await translate_page_image(b"original-bytes", source_lang="ENG")

    assert mock_client.post.call_count == 3
    assert mock_sleep.call_args_list == [call(2), call(4)]


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_skips_already_done_pages():
    chapter_id = "valirscans:the-counts-secret-maid:101"
    mock_pages = [
        PageItem(page_index=1, image_url="https://media.valirscans.org/p1.webp"),
        PageItem(page_index=2, image_url="https://media.valirscans.org/p2.webp"),
    ]

    async def mock_download_pages(pages):
        for p in pages:
            yield p, f"bytes-{p.page_index}".encode()

    mock_provider = MagicMock()
    mock_provider.extract_chapter_pages = AsyncMock(return_value=mock_pages)
    mock_provider.download_pages = mock_download_pages

    mock_reg_inst = MagicMock()
    mock_reg_inst.get_provider.return_value = mock_provider

    # Page 1 is already DONE with an image_url
    existing_done_page = Page(
        chapter_id=chapter_id,
        page_index=1,
        status=TranslationStatus.DONE,
        image_url="https://r2/existing_p1.png",
    )
    # Page 2 is PENDING
    pending_page = Page(
        chapter_id=chapter_id,
        page_index=2,
        status=TranslationStatus.PENDING,
        image_url=None,
    )
    chapter_record = Chapter(id=chapter_id, total_pages=0, status=TranslationStatus.PENDING)

    def make_scalar_res(val):
        res = MagicMock()
        res.scalar_one_or_none.return_value = val
        return res

    mock_session = AsyncMock()

    async def mock_execute(statement, *args, **kwargs):
        stmt_str = str(statement).lower()
        if "from chapters" in stmt_str or "from chapter" in stmt_str:
            return make_scalar_res(chapter_record)
        if "from pages" in stmt_str or "from page" in stmt_str:
            try:
                p_idx = statement.compile().params.get("page_index_1")
            except Exception:
                p_idx = None
            if p_idx == 1:
                return make_scalar_res(existing_done_page)
            elif p_idx == 2:
                return make_scalar_res(pending_page)
        return make_scalar_res(None)

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    class MockSessionCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_redis = AsyncMock()

    with patch("src.worker.get_registry", return_value=mock_reg_inst), \
         patch("src.worker.AsyncSessionLocal", return_value=MockSessionCtx()), \
         patch("src.worker.translate_page_image", new=AsyncMock(return_value=b"translated-bytes")) as mock_trans, \
         patch("src.worker.upload_image_to_r2", new=AsyncMock(return_value="https://r2/new_p2.png")) as mock_upload, \
         patch("src.worker.redis.from_url", new=AsyncMock(return_value=mock_redis)):

        await scrape_and_download_chapter(
            ctx={},
            provider_name="valirscans",
            chapter_id=chapter_id,
            chapter_url="https://valirscans.org/ch101",
            force_translate=True,
        )

    # Page 1 was already DONE -> should NOT be translated or uploaded
    mock_trans.assert_called_once_with(b"bytes-2", source_lang="ENG")
    mock_upload.assert_called_once_with(b"translated-bytes", f"{chapter_id}/2.png")

    # Both pages should have SSE notifications
    assert mock_redis.publish.call_count == 2
    mock_redis.publish.assert_any_call(
        f"chapter:{chapter_id}",
        json.dumps({"page_index": 1, "url": "https://r2/existing_p1.png"}),
    )
    mock_redis.publish.assert_any_call(
        f"chapter:{chapter_id}",
        json.dumps({"page_index": 2, "url": "https://r2/new_p2.png"}),
    )
    # Chapter finished successfully
    assert chapter_record.status == TranslationStatus.DONE


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_reuses_redis_from_ctx():
    chapter_id = "valirscans:the-counts-secret-maid:101"
    mock_pages = [PageItem(page_index=1, image_url="https://media.valirscans.org/p1.webp")]

    async def mock_download_pages(pages):
        for p in pages:
            yield p, b"img-bytes"

    mock_provider = MagicMock()
    mock_provider.extract_chapter_pages = AsyncMock(return_value=mock_pages)
    mock_provider.download_pages = mock_download_pages

    mock_reg_inst = MagicMock()
    mock_reg_inst.get_provider.return_value = mock_provider

    mock_redis = AsyncMock()

    with patch("src.worker.get_registry", return_value=mock_reg_inst), \
         patch("src.worker.AsyncSessionLocal", side_effect=MockSessionContext), \
         patch("src.worker.upload_image_to_r2", new=AsyncMock(return_value="https://r2/dest.png")), \
         patch("src.worker.redis.from_url") as mock_from_url:

        await scrape_and_download_chapter(
            ctx={"redis": mock_redis},
            provider_name="valirscans",
            chapter_id=chapter_id,
            chapter_url="https://valirscans.org/ch101",
            force_translate=False,
        )

    # Verified redis was reused from ctx
    mock_from_url.assert_not_called()
    mock_redis.publish.assert_called_once()
    mock_redis.aclose.assert_not_called()


@pytest.mark.asyncio
async def test_worker_startup_purges_orphan_locks():
    mock_redis = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=["arq:in-progress:job1", "arq:in-progress:job2"])
    mock_redis.connection_pool = MagicMock()
    mock_redis.connection_pool.connection_kwargs = {}

    await startup({"redis": mock_redis})

    mock_redis.keys.assert_awaited_once_with("arq:in-progress:*")
    mock_redis.delete.assert_awaited_once_with("arq:in-progress:job1", "arq:in-progress:job2")
    assert mock_redis.connection_pool.connection_kwargs["socket_keepalive"] is True
    assert mock_redis.connection_pool.connection_kwargs["health_check_interval"] == 30
    assert mock_redis.connection_pool.connection_kwargs["retry_on_timeout"] is True


@pytest.mark.asyncio
async def test_worker_startup_no_orphan_locks():
    mock_redis = AsyncMock()
    mock_redis.connection_pool = MagicMock()
    mock_redis.connection_pool.connection_kwargs = {}
    mock_redis.keys = AsyncMock(return_value=[])

    await startup({"redis": mock_redis})

    mock_redis.keys.assert_awaited_once_with("arq:in-progress:*")
    mock_redis.delete.assert_not_called()


def test_worker_settings_configured():
    assert WorkerSettings.job_timeout == 600
    assert WorkerSettings.on_startup == startup
    assert WorkerSettings.redis_settings.conn_timeout == 10
    assert WorkerSettings.redis_settings.retry_on_timeout is True
    assert WorkerSettings.redis_settings.conn_retries == 10


@pytest.mark.asyncio
async def test_main_startup_configures_redis_keepalive():
    from src.main import startup as main_startup

    mock_pool = MagicMock()
    mock_pool.connection_pool = MagicMock()
    mock_pool.connection_pool.connection_kwargs = {}

    with patch("src.main.create_pool", new=AsyncMock(return_value=mock_pool)), \
         patch("src.main.get_redis_settings", new=AsyncMock()):
        await main_startup()

    assert mock_pool.connection_pool.connection_kwargs["socket_keepalive"] is True
    assert mock_pool.connection_pool.connection_kwargs["health_check_interval"] == 30
    assert mock_pool.connection_pool.connection_kwargs["retry_on_timeout"] is True


@pytest.mark.asyncio
async def test_warmup_manga_translator_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    class MockClientContext:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()):
        await warmup_manga_translator()

    mock_client.post.assert_called_once()
    call_args, call_kwargs = mock_client.post.call_args
    assert "/translate/with-form/image" in call_args[0]
    assert "image" in call_kwargs["files"]
    assert "config" in call_kwargs["data"]

    sent_config = json.loads(call_kwargs["data"]["config"])
    assert sent_config["translator"] == {"translator": "none", "target_lang": "PTB"}
    assert sent_config["inpainter"] == {"inpainter": "lama_mpe"}
    assert sent_config["detector"] == {
        "unclip_ratio": 2.4,
        "box_threshold": 0.6,
        "text_threshold": 0.2,
    }


@pytest.mark.asyncio
async def test_warmup_manga_translator_handles_error():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=RuntimeError("GPU warmup connection failure"))

    class MockClientContext:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()):
        # Should not raise exception
        await warmup_manga_translator()


@pytest.mark.asyncio
async def test_worker_startup_dispatches_warmup_task():
    mock_redis = AsyncMock()
    mock_redis.connection_pool = MagicMock()
    mock_redis.connection_pool.connection_kwargs = {}
    mock_redis.keys = AsyncMock(return_value=[])

    with patch("src.worker.warmup_manga_translator", new=AsyncMock()) as mock_warmup:
        await startup({"redis": mock_redis})
        # Allow event loop to process task
        await asyncio.sleep(0.01)
        mock_warmup.assert_called_once()
