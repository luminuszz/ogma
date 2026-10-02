from pathlib import Path

from arq import create_pool
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from src.mangadex import fetch_chapter_pages, fetch_manga_feed
from src.worker import get_redis_settings

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
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/manga/{chapter_id}")
async def process_chapter(chapter_id: str, background_tasks: BackgroundTasks):
    try:
        pages = await fetch_chapter_pages(chapter_id)
        
        async def enqueue_all(pages):
            import asyncio
            if not pages:
                return
                
            # Prioritize the first page by enqueuing and giving it a head start
            await redis_pool.enqueue_job(
                "process_page",
                chapter_id,
                pages[0]["url"],
                pages[0]["pageIndex"],
                _job_id=f"page_{chapter_id}_{pages[0]['pageIndex']}"
            )
            
            # Pequeno delay para garantir que a primeira página seja pega pelo worker primeiro
            await asyncio.sleep(0.1)

            # Enfileira o restante sequencialmente para manter a ordem de prioridade
            for page in pages[1:]:
                await redis_pool.enqueue_job(
                    "process_page",
                    chapter_id,
                    page["url"],
                    page["pageIndex"],
                    _job_id=f"page_{chapter_id}_{page['pageIndex']}"
                )

        # Enqueue jobs em background concorrentemente
        background_tasks.add_task(enqueue_all, pages)
            
        # Store total pages in Redis so the status endpoint can read it reliably
        # without querying heavy BullMQ/ARQ dependencies
        await redis_pool.set(f"chapter_total_{chapter_id}", len(pages))  # type: ignore
            
        return {
            "status": "queued",
            "chapterId": chapter_id,
            "totalPages": len(pages),
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manga/{chapter_id}/status")
async def chapter_status(chapter_id: str):
    try:
        total_str = await redis_pool.get(f"chapter_total_{chapter_id}")  # type: ignore
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
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/clear-cache")
async def clear_cache():
    try:
        import shutil
        
        # 1. Clear Redis (apenas chaves referentes ao ARQ e ao controle de capítulos do projeto)
        keys_to_delete = []
        async for key in redis_pool.scan_iter("arq:*"):
            keys_to_delete.append(key)
        async for key in redis_pool.scan_iter("chapter_total_*"):
            keys_to_delete.append(key)
        
        if keys_to_delete:
            await redis_pool.delete(*keys_to_delete)
        
        # 2. Clear local disk storage (/data directory)
        data_dir = Path("/data")
        if data_dir.exists():
            for item in data_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                    
        return {"success": True, "message": "Redis queue and local storage cleared successfully."}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
