import json
import os
from pathlib import Path

import httpx
from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ML_URL = os.getenv("WORKER_ML_URL", "http://manga-translator:5003")

async def get_redis_settings():
    return RedisSettings.from_dsn(REDIS_URL)

async def process_page(ctx, chapter_id: str, url: str, page_index: int):
    """Downloads the image from MangaDex and sends it to manga-image-translator."""
    try:
        # 1. Download image
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            image_bytes = resp.content

        config = {
               "source_lang": "SPA", # Mantém o idioma dinâmico (ENG/SPA)
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

        # 3. Save to disk for the frontend
        data_dir = Path("/data") / chapter_id
        data_dir.mkdir(parents=True, exist_ok=True)

        final_path = data_dir / f"{page_index}.png"
        with open(final_path, "wb") as f:  # noqa: ASYNC230
            f.write(translated_bytes)

        return {"status": "ok", "path": str(final_path)}

    except Exception as e:
        print(f"Failed to process page {page_index}: {e}")
        raise

class WorkerSettings:
    functions: list = [process_page]  # noqa: RUF012
    max_jobs = 1
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
