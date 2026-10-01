import os
import json
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from arq import create_pool
from src.worker import get_redis_settings
from src.mangadex import fetch_manga_feed, fetch_chapter_pages

app = FastAPI()
redis_pool = None

@app.on_event("startup")
async def startup():
    global redis_pool
    redis_pool = await create_pool(await get_redis_settings())
    
# Mount static files just like Express
app.mount("/data", StaticFiles(directory="/data"), name="data")

@app.get("/api/manga/{manga_id}/chapters")
async def get_chapters(manga_id: str):
    try:
        chapters = await fetch_manga_feed(manga_id)
        return {"chapters": chapters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/manga/{chapter_id}")
async def process_chapter(chapter_id: str):
    try:
        pages = await fetch_chapter_pages(chapter_id)
        
        # Enqueue jobs
        for page in pages:
            await redis_pool.enqueue_job(
                "process_page",
                chapter_id,
                page["url"],
                page["pageIndex"],
                _job_id=f"page_{chapter_id}_{page['pageIndex']}"
            )
            
        # Store total pages in Redis so the status endpoint can read it reliably
        # without querying heavy BullMQ/ARQ dependencies
        redis = redis_pool._redis
        await redis.set(f"chapter_total_{chapter_id}", len(pages))
            
        return {
            "status": "queued",
            "chapterId": chapter_id,
            "totalPages": len(pages),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manga/{chapter_id}/status")
async def chapter_status(chapter_id: str):
    try:
        redis = redis_pool._redis
        
        total_str = await redis.get(f"chapter_total_{chapter_id}")
        if not total_str:
            return {"chapterId": chapter_id, "total": 0, "completed": 0, "failed": 0, "status": "not_found"}
            
        total = int(total_str)
        
        # Count processed pages on disk
        data_dir = Path("/data") / chapter_id
        ready_pages = []
        if data_dir.exists() and total > 0:
            for i in range(total):
                if (data_dir / f"{i}.png").exists():
                    ready_pages.append(i)
                    
        completed = len(ready_pages)
        
        status = "processing"
        if completed == total and total > 0:
            status = "done"
            
        return {
            "chapterId": chapter_id,
            "total": total,
            "completed": completed,
            "failed": 0,
            "status": status,
            "readyPages": ready_pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
