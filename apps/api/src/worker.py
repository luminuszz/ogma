import json
import os

import httpx
from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ML_URL = os.getenv("WORKER_ML_URL", "http://manga-translator:5003")

async def get_redis_settings():
    return RedisSettings.from_dsn(REDIS_URL)

async def process_page(ctx, chapter_id: str, url: str, page_index: int, source_lang: str = "auto"):
    """Downloads the image from MangaDex and sends it to manga-image-translator."""
    try:
        # 1. Download image
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            image_bytes = resp.content

        # Parse source_lang
        lang_map = {
            "en": "ENG", "eng": "ENG",
            "es": "SPA", "es-la": "SPA", "spa": "SPA",
            "pt-br": "POR", "pt": "POR", "por": "POR",
            "ja": "JPN", "jp": "JPN", "jpn": "JPN",
            "ko": "KOR", "kr": "KOR", "kor": "KOR",
            "zh": "CHS", "zh-hk": "CHT"
        }

        parsed_lang = "AUTO"
        if source_lang.lower() in lang_map:
            parsed_lang = lang_map[source_lang.lower()]
        elif source_lang.upper() in ["ENG", "SPA", "JPN", "KOR", "CHS", "CHT", "RUS", "FRA", "GER", "ITA", "POR", "POL", "ARA"]:
            parsed_lang = source_lang.upper()

        config = {
               "source_lang": parsed_lang, # Idioma mapeado e agora dinâmico
               "target_lang": "PTB",
               "translator": {
                   "translator": "custom_openai",
                   "target_lang": "PTB",
                   "prompt": "You are a professional manga translator. Translate the given text accurately to Brazilian Portuguese. STRICT FORMATTING RULES: 1) Return the translation as a single continuous string with NO line breaks or newlines (\n). 2) ALWAYS insert exactly one space after every comma, period, exclamation, and question mark. 3) Never output words glued to punctuation. 4) Output ONLY the translated text, without quotes, notes, or explanations."
               },
               "render": {
                               "direction": "horizontal",
                               "no_hyphenation": True,
                               "font_size_offset": 0,
                               "font_size_minimum": 15
                           },
               "detector": {
                   "unclip_ratio": 2.5
               }

           }

        files = {
            'image': (f"{page_index}.png", image_bytes, 'image/png')
        }
        data = {
            'config': json.dumps(config)
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{WORKER_ML_URL}/translate/with-form/image",
                files=files,
                data=data
            )
            response.raise_for_status()
            translated_bytes = response.content

        # 3. Save to R2 and update database
        from sqlalchemy import select

        from src.db.database import AsyncSessionLocal
        from src.db.models import Page, TranslationStatus
        from src.services.storage import upload_image_to_r2

        destination_path = f"{chapter_id}/{page_index}.png"
        image_url = await upload_image_to_r2(translated_bytes, destination_path)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id, Page.page_index == page_index)
            )
            page_obj = result.scalar_one_or_none()
            if page_obj:
                page_obj.status = TranslationStatus.DONE # type: ignore
                page_obj.image_url = image_url # type: ignore
                await session.commit()

        return {"status": "ok", "url": image_url}

    except Exception as e:
        print(f"Failed to process page {page_index}: {e}")
        from sqlalchemy import select
        from src.db.database import AsyncSessionLocal
        from src.db.models import Page, TranslationStatus
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id, Page.page_index == page_index)
            )
            page_obj = result.scalar_one_or_none()
            if page_obj:
                page_obj.status = TranslationStatus.ERROR # type: ignore
                await session.commit()
        raise

class WorkerSettings:
    functions: list = [process_page]  # noqa: RUF012
    max_jobs = 3
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
