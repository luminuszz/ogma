import asyncio
import base64
import json
import os

import httpx
import redis.asyncio as redis
from arq.connections import RedisSettings
from sqlalchemy import select

from src.db.database import AsyncSessionLocal
from src.db.models import Chapter, Page, TranslationStatus
from src.scrapers.registry import get_registry
from src.services.storage import upload_image_to_r2

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ML_URL = os.getenv("WORKER_ML_URL", "http://manga-translator:5003")
MINIMAL_1X1_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def make_redis_settings(dsn: str = REDIS_URL) -> RedisSettings:
    settings = RedisSettings.from_dsn(dsn)
    settings.conn_retries = 10
    settings.retry_on_timeout = True
    settings.conn_timeout = 10
    return settings


async def get_redis_settings():
    return make_redis_settings()


async def translate_page_image(image_bytes: bytes, source_lang: str = "ENG") -> bytes:
    lang_map = {
        "en": "ENG",
        "eng": "ENG",
        "es": "SPA",
        "es-la": "SPA",
        "spa": "SPA",
        "pt-br": "POR",
        "pt": "POR",
        "por": "POR",
        "ja": "JPN",
        "jp": "JPN",
        "jpn": "JPN",
        "ko": "KOR",
        "kr": "KOR",
        "kor": "KOR",
        "zh": "CHS",
        "zh-hk": "CHT",
    }
    parsed_lang = lang_map.get(source_lang.lower(), source_lang.upper())

    config = {
        "source_lang": parsed_lang,
        "target_lang": "PTB",
        "translator": {
            "translator": "custom_openai",
            "target_lang": "PTB",
            "prompt": (
                "You are a professional manga translator. Translate the given text accurately "
                "to Brazilian Portuguese. STRICT FORMATTING RULES: 1) Return the translation "
                "as a single continuous string with NO line breaks or newlines (\n). 2) ALWAYS "
                "insert exactly one space after every comma, period, exclamation, and question mark. "
                "3) Never output words glued to punctuation. 4) Output ONLY the translated text, "
                "without quotes, notes, or explanations."
            ),
        },
        "inpainter": {"inpainter": "lama_mpe"},
        "render": {
            "direction": "horizontal",
            "alignment": "center",
            "no_hyphenation": False,
            "font_size_offset": -1,
            "font_size_minimum": 12,
        },
        "detector": {
            "detector": "ctd",
            "unclip_ratio": 2.4,
            "box_threshold": 0.6,
            "text_threshold": 0.2,
        },
    }

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            files = {"image": ("page.png", image_bytes, "image/png")}
            data = {"config": json.dumps(config)}

            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{WORKER_ML_URL}/translate/with-form/image", files=files, data=data
                )
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            if attempt == max_retries:
                print(f"Translation failed after {max_retries} attempts: {e}")
                raise
            backoff = 2 * attempt
            print(
                f"Translation attempt {attempt} failed ({e}). Retrying in {backoff}s..."
            )
            await asyncio.sleep(backoff)


async def process_page(
    ctx, chapter_id: str, url: str, page_index: int, source_lang: str = "auto"
):
    """Downloads the image from MangaDex and sends it to manga-image-translator."""
    try:
        # 1. Download image
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            image_bytes = resp.content

        # 2. Translate image
        translated_bytes = await translate_page_image(
            image_bytes, source_lang=source_lang
        )

        # 3. Save to R2 and update database

        destination_path = f"{chapter_id}/{page_index}.png"
        image_url = await upload_image_to_r2(translated_bytes, destination_path)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Page).where(
                    Page.chapter_id == chapter_id, Page.page_index == page_index
                )
            )
            page_obj = result.scalar_one_or_none()
            if page_obj:
                page_obj.status = TranslationStatus.DONE  # type: ignore
                page_obj.image_url = image_url  # type: ignore
                await session.commit()

                # Check if all pages for the chapter are done
                pages_res = await session.execute(
                    select(Page.status).where(Page.chapter_id == chapter_id)
                )
                statuses = pages_res.scalars().all()
                if statuses and all(s == TranslationStatus.DONE for s in statuses):
                    ch_res = await session.execute(
                        select(Chapter).where(Chapter.id == chapter_id)
                    )
                    chapter_obj = ch_res.scalar_one_or_none()
                    if chapter_obj and chapter_obj.status != TranslationStatus.DONE:
                        chapter_obj.status = TranslationStatus.DONE
                        await session.commit()

        r = ctx.get("redis") if ctx else None
        should_close_redis = False
        if r is None:
            r = await redis.from_url(
                REDIS_URL,
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,
            )
            should_close_redis = True

        try:
            await r.publish(f"chapter:{chapter_id}", json.dumps({"page_index": page_index, "url": image_url}))
        finally:
            if should_close_redis:
                await r.aclose()

        return {"status": "ok", "url": image_url}

    except Exception as e:
        print(f"Failed to process page {page_index}: {e}")
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Page).where(
                    Page.chapter_id == chapter_id, Page.page_index == page_index
                )
            )
            page_obj = result.scalar_one_or_none()
            if page_obj:
                page_obj.status = TranslationStatus.ERROR  # type: ignore
                await session.commit()
        raise


async def scrape_and_download_chapter(
    ctx,
    provider_name: str,
    chapter_id: str,
    chapter_url: str,
    force_translate: bool = False,
):
    try:
        registry = get_registry()
        provider = registry.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} not found.")

        # 1. Extract pages using the provider
        pages = await provider.extract_chapter_pages(chapter_url)
        if not pages:
            raise ValueError(f"No pages extracted for chapter {chapter_url}")

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter_obj = result.scalar_one_or_none()
            if chapter_obj:
                chapter_obj.total_pages = len(pages)
                chapter_obj.status = TranslationStatus.PROCESSING

            # Prepare Page records
            for page in pages:
                existing_page = await session.execute(
                    select(Page).where(
                        Page.chapter_id == chapter_id, Page.page_index == page.page_index
                    )
                )
                page_obj = existing_page.scalar_one_or_none()
                if not page_obj:
                    session.add(
                        Page(
                            chapter_id=chapter_id,
                            page_index=page.page_index,
                            status=TranslationStatus.PENDING,
                        )
                    )

            await session.commit()

        # 2. Download and upload each image with provider context
        has_failures = False
        r = ctx.get("redis") if ctx else None
        should_close_redis = False
        if r is None:
            r = await redis.from_url(
                REDIS_URL,
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,
            )
            should_close_redis = True

        try:
            async for page, image_bytes in provider.download_pages(pages):
                try:
                    # Checkpoint: verify if page is already completed
                    async with AsyncSessionLocal() as session:
                        res = await session.execute(
                            select(Page).where(
                                Page.chapter_id == chapter_id,
                                Page.page_index == page.page_index,
                            )
                        )
                        existing_page = res.scalar_one_or_none()
                        if (
                            existing_page
                            and existing_page.status == TranslationStatus.DONE
                            and existing_page.image_url
                        ):
                            print(
                                f"Page {page.page_index} for chapter {chapter_id} already completed. Skipping."
                            )
                            await r.publish(
                                f"chapter:{chapter_id}",
                                json.dumps(
                                    {
                                        "page_index": page.page_index,
                                        "url": existing_page.image_url,
                                    }
                                ),
                            )
                            continue

                    dest_path = f"{chapter_id}/{page.page_index}.png"

                    final_bytes = image_bytes
                    if force_translate:
                        try:
                            final_bytes = await translate_page_image(image_bytes, source_lang="ENG")
                        except Exception as trans_err:  # noqa: BLE001
                            has_failures = True
                            print(
                                f"Translation failed for page {page.page_index} in {chapter_id}: {trans_err}. Falling back to original."
                            )
                            final_bytes = image_bytes

                    image_url = await upload_image_to_r2(final_bytes, dest_path)

                    async with AsyncSessionLocal() as session:
                        res = await session.execute(
                            select(Page).where(
                                Page.chapter_id == chapter_id,
                                Page.page_index == page.page_index,
                            )
                        )
                        page_record = res.scalar_one_or_none()
                        if page_record:
                            page_record.status = TranslationStatus.DONE
                            page_record.image_url = image_url
                            await session.commit()

                    # Publish SSE progress update
                    await r.publish(
                        f"chapter:{chapter_id}",
                        json.dumps({"page_index": page.page_index, "url": image_url}),
                    )

                except Exception as e:  # noqa: BLE001
                    has_failures = True
                    print(f"Error processing page {page.page_index} for {chapter_id}: {e}")
                    async with AsyncSessionLocal() as session:
                        res = await session.execute(
                            select(Page).where(
                                Page.chapter_id == chapter_id,
                                Page.page_index == page.page_index,
                            )
                        )
                        p_rec = res.scalar_one_or_none()
                        if p_rec:
                            p_rec.status = TranslationStatus.ERROR
                            await session.commit()
        except Exception as e:  # noqa: BLE001
            has_failures = True
            print(f"Error downloading pages for chapter {chapter_id}: {e}")
        finally:
            if should_close_redis:
                await r.aclose()

        # 3. Mark Chapter as DONE or ERROR
        async with AsyncSessionLocal() as session:
            ch_res = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter_obj = ch_res.scalar_one_or_none()
            if chapter_obj:
                chapter_obj.status = (
                    TranslationStatus.ERROR if has_failures else TranslationStatus.DONE
                )
                await session.commit()

    except Exception as e:
        print(f"Error executing scrape_and_download_chapter for {chapter_id}: {e}")
        try:
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
                ch = res.scalar_one_or_none()
                if ch and ch.status != TranslationStatus.DONE:
                    ch.status = TranslationStatus.ERROR
                    await session.commit()
        except Exception as db_err:
            print(f"Failed to update chapter {chapter_id} to ERROR status: {db_err}")
        raise


async def warmup_manga_translator() -> None:
    try:
        config = {
            "translator": {"translator": "none", "target_lang": "PTB"},
            "inpainter": {"inpainter": "lama_mpe"},
            "detector": {
                "detector": "ctd",
                "unclip_ratio": 2.4,
                "box_threshold": 0.6,
                "text_threshold": 0.2,
            },
        }
        files = {"image": ("warmup.png", MINIMAL_1X1_PNG, "image/png")}
        data = {"config": json.dumps(config)}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{WORKER_ML_URL}/translate/with-form/image",
                files=files,
                data=data,
            )
            resp.raise_for_status()
        print("Translator GPU models pre-warmed successfully")
    except Exception as e:
        print(f"Warning: Failed to pre-warm translator GPU models: {e}")


async def startup(ctx):
    r = ctx.get("redis")
    if r:
        if hasattr(r, "connection_pool") and hasattr(r.connection_pool, "connection_kwargs"):
            r.connection_pool.connection_kwargs.update(
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,
            )
        keys = await r.keys("arq:in-progress:*")
        if keys:
            await r.delete(*keys)
            print(f"Purged {len(keys)} orphan in-progress keys on startup: {keys}")

    asyncio.create_task(warmup_manga_translator())


class WorkerSettings:
    functions: list = [process_page, scrape_and_download_chapter]  # noqa: RUF012
    max_jobs = 1
    job_timeout = 600
    redis_settings = make_redis_settings()
    on_startup = startup
