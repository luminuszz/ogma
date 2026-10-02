from pathlib import Path

from arq import create_pool
from fastapi import BackgroundTasks, FastAPI, HTTPException

from src.mangadex import fetch_chapter_metadata, fetch_chapter_pages, fetch_manga_feed
from src.worker import get_redis_settings

app = FastAPI()
redis_pool = None

@app.on_event("startup")
async def startup():
    global redis_pool
    redis_pool = await create_pool(await get_redis_settings())
    


@app.get("/api/manga/{manga_id}/chapters")
async def get_chapters(manga_id: str):
    try:
        chapters = await fetch_manga_feed(manga_id)
        return {"chapters": chapters}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/manga/{chapter_id}")
async def process_chapter(chapter_id: str, background_tasks: BackgroundTasks, source_lang: str = "auto"):
    try:
        pages = await fetch_chapter_pages(chapter_id)
        meta = await fetch_chapter_metadata(chapter_id)
        
        from sqlalchemy import select

        from src.db.database import AsyncSessionLocal
        from src.db.models import Chapter, Manga, Page, TranslationStatus
        
        async with AsyncSessionLocal() as session:
            manga_result = await session.execute(select(Manga).where(Manga.id == meta["manga_id"]))
            manga_obj = manga_result.scalar_one_or_none()
            if not manga_obj:
                manga_obj = Manga(id=meta["manga_id"], title=meta["title"])
                session.add(manga_obj)
            else:
                manga_obj.title = meta["title"]  # type: ignore

            result = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter_obj = result.scalar_one_or_none()
            
            if not chapter_obj:
                chapter_obj = Chapter(
                    id=chapter_id,
                    manga_id=meta["manga_id"],
                    chapter_number=meta["chapter"],
                    total_pages=len(pages),
                    status=TranslationStatus.PROCESSING
                )
                session.add(chapter_obj)
            else:
                chapter_obj.manga_id = meta["manga_id"]  # type: ignore
                chapter_obj.chapter_number = meta["chapter"]  # type: ignore
                chapter_obj.total_pages = len(pages) # type: ignore
                chapter_obj.status = TranslationStatus.PROCESSING # type: ignore
                
            # Fetch all existing pages for this chapter in one query to avoid N+1 problem
            existing_pages_result = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id)
            )
            existing_pages = {p.page_index: p for p in existing_pages_result.scalars().all()}
            
            pages_to_add = []
            for page in pages:
                page_idx = page["pageIndex"]
                if page_idx in existing_pages:
                    existing_pages[page_idx].status = TranslationStatus.PENDING # type: ignore
                else:
                    pages_to_add.append(
                        Page(
                            chapter_id=chapter_id,
                            page_index=page_idx,
                            status=TranslationStatus.PENDING
                        )
                    )
            
            if pages_to_add:
                session.add_all(pages_to_add)
            await session.commit()

        async def enqueue_all(pages):
            import asyncio
            if not pages:
                return
                
            lang_to_use = source_lang if source_lang != "auto" else meta.get("language", "auto")

            # Prioritize the first page by enqueuing and giving it a head start
            await redis_pool.enqueue_job(
                "process_page",
                chapter_id,
                pages[0]["url"],
                pages[0]["pageIndex"],
                lang_to_use,
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
                    lang_to_use,
                    _job_id=f"page_{chapter_id}_{page['pageIndex']}"
                )

        # Enqueue jobs em background concorrentemente
        background_tasks.add_task(enqueue_all, pages)
            
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
        from sqlalchemy import select

        from src.db.database import AsyncSessionLocal
        from src.db.models import Chapter, Page, TranslationStatus
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter_obj = result.scalar_one_or_none()
            
            if not chapter_obj:
                return {"chapterId": chapter_id, "total": 0, "completed": 0, "failed": 0, "status": "not_found", "readyPages": []}
                
            total = chapter_obj.total_pages
            
            # Count done pages
            pages_result = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id)
            )
            pages = pages_result.scalars().all()
            
            ready_pages = [{"pageIndex": p.page_index, "url": p.image_url} for p in pages if p.status == TranslationStatus.DONE]
            failed = len([p for p in pages if p.status == TranslationStatus.ERROR])
            completed = len(ready_pages)
            
            status = "processing"
            if completed == total and total > 0:
                status = "done"
                chapter_obj.status = TranslationStatus.DONE # type: ignore
                await session.commit()
                
            return {
                "chapterId": chapter_id,
                "total": total,
                "completed": completed,
                "failed": failed,
                "status": status,
                "readyPages": ready_pages
            }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manga/library")
async def get_library():
    try:
        from sqlalchemy import func, select

        from src.db.database import AsyncSessionLocal
        from src.db.models import Chapter, Manga, Page, TranslationStatus
        
        async with AsyncSessionLocal() as session:
            stmt = select(Chapter, Manga.title).join(Manga, Chapter.manga_id == Manga.id)
            result = await session.execute(stmt)
            rows = result.all()
            
            library = []
            for chapter, manga_title in rows:
                pages_stmt = select(func.count(Page.id)).where(
                    Page.chapter_id == chapter.id, 
                    Page.status == TranslationStatus.DONE
                )
                pages_result = await session.execute(pages_stmt)
                downloaded = pages_result.scalar() or 0
                
                library.append({
                    "id": chapter.id,
                    "title": manga_title,
                    "chapter": chapter.chapter_number,
                    "downloaded": downloaded,
                    "total": chapter.total_pages
                })
                
        return {"library": library}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/manga/{chapter_id}")
async def delete_chapter(chapter_id: str):
    try:
        from sqlalchemy import delete
        
        from src.db.database import AsyncSessionLocal
        from src.db.models import Chapter, Page
        from src.services.storage import delete_chapter_from_r2
        
        async with AsyncSessionLocal() as session:
            # Delete pages from DB
            await session.execute(delete(Page).where(Page.chapter_id == chapter_id))
            # Delete chapter from DB
            result = await session.execute(delete(Chapter).where(Chapter.id == chapter_id))
            await session.commit()
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Delete from R2
        try:
            await delete_chapter_from_r2(chapter_id)
        except Exception as e:
            print(f"Failed to delete chapter {chapter_id} from R2: {e}")
            
        return {"status": "deleted"}
    except HTTPException:
        raise
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
