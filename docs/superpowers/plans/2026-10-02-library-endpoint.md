# Backend API Implementation Plan: Library Endpoint

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the real `GET /api/manga/library` endpoint in FastAPI to replace the frontend mock, leveraging the new PostgreSQL database to fetch and display the library correctly.

**Architecture:** 
- Fetch metadata (title, chapter number) from MangaDex when a download starts (`POST /api/manga/{chapter_id}`).
- Store this metadata securely in the `Manga` and `Chapter` PostgreSQL tables.
- Expose `GET /api/manga/library` that queries the database, retrieving the manga title, chapter status, and total pages downloaded.
- Remove the temporary frontend mock and connect to the real API.

**Tech Stack:** FastAPI, Python, PostgreSQL, SQLAlchemy (Async), React Query.

---

### Task 1: Fetch and Store Metadata in PostgreSQL on Download Start

**Files:**
- Modify: `apps/api/src/db/models.py` (Add `chapter_number` to `Chapter`)
- Modify: `apps/api/src/mangadex.py`
- Modify: `apps/api/src/main.py`

**Interfaces:**
- Produces: `fetch_chapter_metadata` function in `mangadex.py`.
- Produces: Updated database schema to hold manga title and chapter number.

- [ ] **Step 1: Add `chapter_number` to Chapter Model**
In `apps/api/src/db/models.py`, add the column to the `Chapter` model:
```python
    chapter_number = Column(String, nullable=True)
```
*(Also create an alembic migration for this field: `alembic revision --autogenerate -m "add chapter_number"`, and run it).*

- [ ] **Step 2: Add `fetch_chapter_metadata` to mangadex.py**
```python
async def fetch_chapter_metadata(chapter_id: str) -> dict:
    url = f"https://api.mangadex.org/chapter/{chapter_id}?includes[]=manga"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            return {"manga_id": chapter_id, "title": "Unknown Title", "chapter": "N/A"}
        data = response.json()
        
    attrs = data.get("data", {}).get("attributes", {})
    chapter_number = attrs.get("chapter") or "N/A"
    
    # Extract Manga Title from relationships
    manga_id = chapter_id
    manga_title = "Unknown Title"
    for rel in data.get("data", {}).get("relationships", []):
        if rel.get("type") == "manga":
            manga_id = rel.get("id")
            manga_title = rel.get("attributes", {}).get("title", {}).get("en") or "Unknown Title"
            break
            
    return {
        "manga_id": manga_id,
        "title": manga_title,
        "chapter": chapter_number
    }
```

- [ ] **Step 3: Save metadata in `process_chapter` (main.py)**
In `main.py`, fetch the metadata and save it to the DB when registering the chapter:
```python
        # Get metadata
        meta = await fetch_chapter_metadata(chapter_id)
        
        # Insert Manga if not exists, Insert Chapter
        # ... (update the existing SQL insertion logic in process_chapter to include meta["title"] and meta["chapter"])
```

- [ ] **Step 4: Commit**
```bash
git add apps/api/src/main.py apps/api/src/mangadex.py apps/api/src/db/ apps/api/alembic/
git commit -m "feat: fetch and store manga metadata in postgresql on download start"
```

---

### Task 2: Implement the `/api/manga/library` Endpoint

**Files:**
- Modify: `apps/api/src/main.py`

**Interfaces:**
- Produces: `GET /api/manga/library` returning `{"library": [...]}`

- [ ] **Step 1: Add the endpoint to `main.py`**
```python
@app.get("/api/manga/library")
async def get_library():
    try:
        async with AsyncSessionLocal() as session:
            # Query all chapters, joining with Manga to get the title
            from sqlalchemy.orm import selectinload
            from src.db.models import Chapter, Manga, Page, TranslationStatus
            from sqlalchemy.future import select
            
            stmt = select(Chapter, Manga.title).join(Manga, Chapter.manga_id == Manga.id)
            result = await session.execute(stmt)
            rows = result.all()
            
            library = []
            for chapter, manga_title in rows:
                # Count completed pages
                pages_stmt = select(func.count(Page.id)).where(Page.chapter_id == chapter.id, Page.status == TranslationStatus.DONE)
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
```

- [ ] **Step 2: Check Python Quality**
Run `source venv/bin/activate && ruff check apps/api/src/ && mypy apps/api/src/`.

- [ ] **Step 3: Commit**
```bash
git add apps/api/src/main.py
git commit -m "feat: implement GET /api/manga/library via PostgreSQL"
```

---

### Task 3: Un-mock Frontend API

**Files:**
- Modify: `apps/web/src/api.ts`

**Interfaces:**
- Consumes: The new real `/api/manga/library` endpoint.

- [ ] **Step 1: Replace Mock in `api.ts`**
Change `getLibrary` back to the real fetch call:
```typescript
  getLibrary: async () => {
    const res = await fetch('/api/manga/library');
    if (!res.ok) throw new Error('Failed to get library');
    return res.json();
  },
```

- [ ] **Step 2: Check TypeScript**
Run `pnpm --filter web run build` and `pnpm --filter web lint`.

- [ ] **Step 3: Commit**
```bash
git add apps/web/src/api.ts
git commit -m "refactor: switch getLibrary from mock to postgres backend API"
```
