import os
import httpx
from arq import create_pool
from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ML_URL = os.getenv("WORKER_ML_URL", "http://localhost:8000")

async def get_redis_settings():
    return RedisSettings.from_dsn(REDIS_URL)

async def process_page(ctx, chapter_id: str, url: str, page_index: int):
    """Hits the worker-ml API to process a single page."""
    payload = {
        "url": url,
        "chapterId": chapter_id,
        "pageId": str(page_index)
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(f"{WORKER_ML_URL}/process-page", json=payload)
        response.raise_for_status()
        return response.json()

class WorkerSettings:
    functions = [process_page]
    max_jobs = 3 # Concurrency of 3 to match TS queue
    
    @classmethod
    async def get_redis_settings(cls):
        return await get_redis_settings()
