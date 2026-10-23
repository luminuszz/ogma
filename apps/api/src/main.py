import asyncio
import difflib
import os
import re
import shutil
from pathlib import Path

import httpx
import redis.asyncio as redis
from arq import create_pool
from fastapi import BackgroundTasks, FastAPI, HTTPException
from sqlalchemy import delete, func, select
from sse_starlette.sse import EventSourceResponse

from src.db.database import AsyncSessionLocal
from src.db.models import Chapter, Manga, Page, TranslationStatus
from src.mangadex import fetch_chapter_metadata, fetch_chapter_pages, fetch_manga_feed
from src.scrapers.base import ChapterItem
from src.scrapers.registry import get_registry
from src.services.storage import delete_chapter_from_r2
from src.worker import get_redis_settings

app = FastAPI()
redis_pool = None


@app.on_event("startup")
async def startup():
    global redis_pool
    redis_pool = await create_pool(await get_redis_settings())


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

@app.get("/api/manga/{chapter_id}/stream")
async def stream_chapter(chapter_id: str):
    async def event_generator():
        r = await redis.from_url(REDIS_URL)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"chapter:{chapter_id}")
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None:
                    yield {"data": message["data"].decode("utf-8")}
                else:
                    yield {"event": "ping", "data": "ping"}
        finally:
            await pubsub.unsubscribe(f"chapter:{chapter_id}")
            await pubsub.close()
            await r.aclose()
            
    return EventSourceResponse(event_generator())


@app.get("/api/manga/{manga_id}/chapters")
async def get_chapters(manga_id: str):
    try:
        chapters = await fetch_manga_feed(manga_id)
        return {"chapters": chapters}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


from pydantic import BaseModel


class BulkDownloadRequest(BaseModel):
    chapterIds: list[str]
    sourceLang: str = "auto"


async def _process_single_chapter(
    chapter_id: str, background_tasks: BackgroundTasks, source_lang: str = "auto"
):
    try:
        pages = await fetch_chapter_pages(chapter_id)
        meta = await fetch_chapter_metadata(chapter_id)

        async with AsyncSessionLocal() as session:
            manga_result = await session.execute(
                select(Manga).where(Manga.id == meta["manga_id"])
            )
            manga_obj = manga_result.scalar_one_or_none()
            if not manga_obj:
                manga_obj = Manga(id=meta["manga_id"], title=meta["title"])
                session.add(manga_obj)
            else:
                manga_obj.title = meta["title"]  # type: ignore

            result = await session.execute(
                select(Chapter).where(Chapter.id == chapter_id)
            )
            chapter_obj = result.scalar_one_or_none()

            if not chapter_obj:
                chapter_obj = Chapter(
                    id=chapter_id,
                    manga_id=meta["manga_id"],
                    chapter_number=meta["chapter"],
                    total_pages=len(pages),
                    status=TranslationStatus.PROCESSING,
                )
                session.add(chapter_obj)
            else:
                chapter_obj.manga_id = meta["manga_id"]  # type: ignore
                chapter_obj.chapter_number = meta["chapter"]  # type: ignore
                chapter_obj.total_pages = len(pages)  # type: ignore
                chapter_obj.status = TranslationStatus.PROCESSING  # type: ignore

            # Fetch all existing pages for this chapter in one query to avoid N+1 problem
            existing_pages_result = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id)
            )
            existing_pages = {
                p.page_index: p for p in existing_pages_result.scalars().all()
            }

            pages_to_add = []
            pages_to_enqueue = []

            for page in pages:
                page_idx = page["pageIndex"]
                if page_idx in existing_pages:
                    if existing_pages[page_idx].status != TranslationStatus.DONE:
                        existing_pages[page_idx].status = TranslationStatus.PENDING  # type: ignore
                        pages_to_enqueue.append(page)
                else:
                    pages_to_add.append(
                        Page(
                            chapter_id=chapter_id,
                            page_index=page_idx,
                            status=TranslationStatus.PENDING,
                        )
                    )
                    pages_to_enqueue.append(page)

            if pages_to_add:
                session.add_all(pages_to_add)
            await session.commit()

        async def enqueue_all(pages_to_process):
            if not pages_to_process:
                return

            lang_to_use = (
                source_lang if source_lang != "auto" else meta.get("language", "auto")
            )

            # Prioritize the first page by enqueuing and giving it a head start
            await redis_pool.enqueue_job(
                "process_page",
                chapter_id,
                pages_to_process[0]["url"],
                pages_to_process[0]["pageIndex"],
                lang_to_use,
                _job_id=f"page_{chapter_id}_{pages_to_process[0]['pageIndex']}",
            )

            # Pequeno delay para garantir que a primeira página seja pega pelo worker primeiro
            await asyncio.sleep(0.1)

            # Enfileira o restante sequencialmente para manter a ordem de prioridade
            for page in pages_to_process[1:]:
                await redis_pool.enqueue_job(
                    "process_page",
                    chapter_id,
                    page["url"],
                    page["pageIndex"],
                    lang_to_use,
                    _job_id=f"page_{chapter_id}_{page['pageIndex']}",
                )

        # Enqueue jobs em background concorrentemente apenas para as páginas faltantes
        background_tasks.add_task(enqueue_all, pages_to_enqueue)

        return {
            "status": "queued",
            "chapterId": chapter_id,
            "totalPages": len(pages),
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/manga/bulk")
async def process_bulk_chapters(
    request: BulkDownloadRequest, background_tasks: BackgroundTasks
):
    results = []
    for chapter_id in request.chapterIds:
        result = await _process_single_chapter(
            chapter_id, background_tasks, request.sourceLang
        )
        results.append(result)
    return {"status": "queued", "results": results}


@app.post("/api/manga/{chapter_id}")
async def process_chapter(
    chapter_id: str, background_tasks: BackgroundTasks, source_lang: str = "auto"
):
    return await _process_single_chapter(chapter_id, background_tasks, source_lang)


@app.post("/api/manga/{chapter_id}/retry")
async def retry_chapter(chapter_id: str, background_tasks: BackgroundTasks):
    try:
        from src.mangadex import fetch_chapter_metadata, fetch_chapter_pages

        if ":" in chapter_id:
            import time
            parts = chapter_id.split(":")
            provider_name = parts[0]
            registry = get_registry()
            provider = registry.get_provider(provider_name)
            if not provider:
                raise HTTPException(status_code=400, detail=f"Provedor {provider_name} não encontrado.")

            async with AsyncSessionLocal() as session:
                ch_res = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
                ch_obj = ch_res.scalar_one_or_none()
                if not ch_obj:
                    raise HTTPException(status_code=404, detail="Capítulo não encontrado.")
                ch_obj.status = TranslationStatus.PROCESSING
                await session.commit()

            ch_url = ""
            force_translate = False
            if provider_name == "lycantoons" and len(parts) >= 3:
                slug, num = parts[1], parts[2]
                ch_url = f"https://lycantoons.com/series/{slug}/{num}"
            elif provider_name == "valirscans" and len(parts) >= 3:
                slug, num = parts[1], parts[2]
                ch_url = f"https://valirscans.org/series/comic/{slug}/chapter/{num}"
                force_translate = True

            job_id = f"scrape_{chapter_id}"
            try:
                await redis_pool.delete(f"arq:result:{job_id}")
            except Exception:
                pass
            await redis_pool.enqueue_job(
                "scrape_and_download_chapter",
                provider_name,
                chapter_id,
                ch_url,
                force_translate,
                _job_id=job_id,
            )
            return {"status": "retrying"}

        pages_data = await fetch_chapter_pages(chapter_id)
        meta = await fetch_chapter_metadata(chapter_id)
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
            chapter_obj = result.scalar_one_or_none()
            
            if not chapter_obj:
                raise HTTPException(status_code=404, detail="Chapter not found")
                
            pages_result = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id, Page.status == TranslationStatus.ERROR)
            )
            failed_pages = pages_result.scalars().all()
            
            if not failed_pages:
                return {"status": "no_failed_pages"}
                
            for page in failed_pages:
                page.status = TranslationStatus.PENDING # type: ignore
                
            chapter_obj.status = TranslationStatus.PROCESSING # type: ignore
            await session.commit()
            
            lang_to_use = meta.get("language", "auto")
            original_urls = {p["pageIndex"]: p["url"] for p in pages_data}
            
            async def enqueue_failed():
                for page in failed_pages:
                    url = original_urls.get(page.page_index)
                    if url:
                        await redis_pool.enqueue_job(
                            "process_page",
                            chapter_id,
                            url,
                            page.page_index,
                            lang_to_use,
                            _job_id=f"page_{chapter_id}_{page.page_index}"
                        )
                        
            background_tasks.add_task(enqueue_failed)
                
        return {"status": "retrying"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manga/{chapter_id}/status")
async def chapter_status(chapter_id: str):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Chapter).where(Chapter.id == chapter_id)
            )
            chapter_obj = result.scalar_one_or_none()

            if not chapter_obj:
                return {
                    "chapterId": chapter_id,
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "status": "not_found",
                    "readyPages": [],
                }

            total = chapter_obj.total_pages

            # Count done pages
            pages_result = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id)
            )
            pages = pages_result.scalars().all()

            ready_pages = [
                {"pageIndex": p.page_index, "url": p.image_url}
                for p in pages
                if p.status == TranslationStatus.DONE
            ]
            failed = len([p for p in pages if p.status == TranslationStatus.ERROR])
            completed = len(ready_pages)

            status = "processing"
            if completed + failed == total and total > 0:
                status = "done" if failed == 0 else "error"
                chapter_obj.status = (
                    TranslationStatus.DONE if failed == 0 else TranslationStatus.ERROR
                )  # type: ignore
                await session.commit()

            return {
                "chapterId": chapter_id,
                "total": total,
                "completed": completed,
                "failed": failed,
                "status": status,
                "readyPages": ready_pages,
            }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manga/library")
async def get_library():
    try:
        async with AsyncSessionLocal() as session:
            downloaded_sq = (
                select(Page.chapter_id, func.count(Page.id).label("downloaded"))
                .where(Page.status == TranslationStatus.DONE)
                .group_by(Page.chapter_id)
            ).subquery()

            stmt = (
                select(Chapter, Manga.title, func.coalesce(downloaded_sq.c.downloaded, 0).label("downloaded"))
                .join(Manga, Chapter.manga_id == Manga.id)
                .outerjoin(downloaded_sq, Chapter.id == downloaded_sq.c.chapter_id)
            )
            result = await session.execute(stmt)
            rows = result.all()

            library = []
            for chapter, manga_title, downloaded in rows:
                library.append(
                    {
                        "id": chapter.id,
                        "title": manga_title,
                        "chapter": chapter.chapter_number,
                        "downloaded": downloaded,
                        "total": chapter.total_pages,
                        "status": chapter.status.value if hasattr(chapter.status, 'value') else chapter.status
                    }
                )

        return {"library": library}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/manga/{chapter_id}")
async def delete_chapter(chapter_id: str):
    try:
        async with AsyncSessionLocal() as session:
            # Delete pages from DB
            await session.execute(delete(Page).where(Page.chapter_id == chapter_id))
            # Delete chapter from DB
            result = await session.execute(
                delete(Chapter).where(Chapter.id == chapter_id)
            )
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

        return {
            "success": True,
            "message": "Redis queue and local storage cleared successfully.",
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


class ExistingMangaSummary(BaseModel):
    id: str
    title: str
    existingChapterNumbers: list[str]


def find_suggested_manga_id(scraped_title: str, existing_mangas: list[ExistingMangaSummary]) -> str | None:
    if not existing_mangas or not scraped_title:
        return None
    scraped_norm = re.sub(r"[^a-zA-Z0-9 ]", "", scraped_title.lower())
    best_id = None
    best_ratio = 0.0
    for m in existing_mangas:
        m_norm = re.sub(r"[^a-zA-Z0-9 ]", "", (m.title or "").lower())
        ratio = difflib.SequenceMatcher(None, scraped_norm, m_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_id = m.id
    return best_id if best_ratio >= 0.3 else None


class ScraperPreviewRequest(BaseModel):
    url: str


class ScraperStartRequest(BaseModel):
    provider: str
    mangaId: str
    title: str
    chapters: list[ChapterItem]
    forceTranslate: bool = False


@app.post("/api/scraper/preview")
async def scraper_preview(req: ScraperPreviewRequest):
    registry = get_registry()
    provider = registry.get_provider_for_url(req.url)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail=f"Nenhum provedor suportado para a URL: {req.url}",
        )
    try:
        preview = await provider.extract_manga_info(req.url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"Erro ao extrair dados da obra: {e!s}"
        )

    existing_works: list[ExistingMangaSummary] = []
    try:
        async with AsyncSessionLocal() as session:
            mangas_res = await session.execute(select(Manga))
            mangas = mangas_res.scalars().all()

            chapters_res = await session.execute(
                select(Chapter.manga_id, Chapter.chapter_number)
            )
            chapters_rows = chapters_res.all()

            chapters_by_manga: dict[str, list[str]] = {}
            for m_id, ch_num in chapters_rows:
                if m_id and ch_num is not None:
                    chapters_by_manga.setdefault(m_id, []).append(str(ch_num))

            existing_works = [
                ExistingMangaSummary(
                    id=m.id,
                    title=m.title or "",
                    existingChapterNumbers=sorted(
                        dict.fromkeys(chapters_by_manga.get(m.id, [])),
                        key=lambda x: float(x) if x.replace(".", "", 1).isdigit() else 999999.0,
                    ),
                )
                for m in mangas
            ]
    except Exception:
        existing_works = []

    suggested_manga_id = find_suggested_manga_id(preview.title, existing_works)

    return {
        "supported": True,
        "provider": preview.provider,
        "mangaId": preview.manga_id,
        "title": preview.title,
        "coverUrl": preview.cover_url,
        "chapters": [c.model_dump() for c in preview.chapters],
        "existingWorks": [m.model_dump() for m in existing_works],
        "suggestedMangaId": suggested_manga_id,
    }


@app.post("/api/scraper/start")
async def scraper_start(req: ScraperStartRequest):
    registry = get_registry()
    if req.provider not in registry.list_providers():
        raise HTTPException(status_code=400, detail="Provedor inválido.")

    async with AsyncSessionLocal() as session:
        # 1. Ensure Manga exists. If it exists, PRESERVE its existing title!
        manga_res = await session.execute(select(Manga).where(Manga.id == req.mangaId))
        manga_obj = manga_res.scalar_one_or_none()
        if not manga_obj:
            manga_obj = Manga(id=req.mangaId, title=req.title)
            session.add(manga_obj)
        # do NOT overwrite manga_obj.title when linking to an existing manga

        # 2. Ensure Chapters exist and point to req.mangaId
        for ch in req.chapters:
            ch_res = await session.execute(
                select(Chapter).where(Chapter.id == ch.id)
            )
            chapter_obj = ch_res.scalar_one_or_none()
            if not chapter_obj:
                chapter_obj = Chapter(
                    id=ch.id,
                    manga_id=req.mangaId,
                    chapter_number=str(ch.number),
                    total_pages=0,
                    status=TranslationStatus.PENDING,
                )
                session.add(chapter_obj)
            else:
                chapter_obj.manga_id = req.mangaId
                chapter_obj.status = TranslationStatus.PENDING

        await session.commit()

    # 3. Enqueue ARQ jobs
    for ch in req.chapters:
        job_id = f"scrape_{ch.id}"
        try:
            await redis_pool.delete(f"arq:result:{job_id}")
        except Exception:
            pass
        await redis_pool.enqueue_job(
            "scrape_and_download_chapter",
            req.provider,
            ch.id,
            ch.url,
            req.forceTranslate,
            _job_id=job_id,
        )

    return {"status": "queued", "count": len(req.chapters)}


@app.get("/api/openrouter/credits")
async def get_openrouter_credits():
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return {
            "enabled": False,
            "remaining": 0.0,
            "usage_daily": 0.0,
            "usage_total": 0.0,
            "limit": None,
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            res_json = resp.json()
            data = res_json.get("data", res_json) if isinstance(res_json, dict) else {}
            if not isinstance(data, dict):
                data = {}
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=503,
            detail=f"OpenRouter API error ({e.response.status_code}): {e.response.text or str(e)}",
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro de conexão com OpenRouter: {e!s}",
        ) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao consultar OpenRouter: {e!s}",
        ) from e

    remaining_val = data.get("limit_remaining")
    if remaining_val is None:
        total_credits = data.get("total_credits")
        if total_credits is not None:
            total_usage = data.get("total_usage", data.get("usage", 0.0))
            try:
                remaining_val = float(total_credits) - float(total_usage or 0.0)
            except (ValueError, TypeError):
                remaining_val = None

    if remaining_val is None:
        effective_budget = data.get("effective_budget")
        if isinstance(effective_budget, dict) and effective_budget.get("remaining_usd") is not None:
            try:
                remaining_val = float(effective_budget["remaining_usd"])
            except (ValueError, TypeError):
                remaining_val = None

    try:
        remaining = round(float(remaining_val), 4) if remaining_val is not None else 0.0
    except (ValueError, TypeError):
        remaining = 0.0

    try:
        usage_daily = round(float(data.get("usage_daily", 0.0) or 0.0), 4)
    except (ValueError, TypeError):
        usage_daily = 0.0

    try:
        usage_total = round(float(data.get("usage", 0.0) or 0.0), 4)
    except (ValueError, TypeError):
        usage_total = 0.0

    limit_val = data.get("limit")
    try:
        limit = round(float(limit_val), 4) if limit_val is not None else None
    except (ValueError, TypeError):
        limit = None

    return {
        "enabled": True,
        "remaining": remaining,
        "usage_daily": usage_daily,
        "usage_total": usage_total,
        "limit": limit,
    }

