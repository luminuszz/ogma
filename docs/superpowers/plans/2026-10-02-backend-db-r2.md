# Backend Implementation Plan (PostgreSQL & Cloudflare R2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the Python backend from local filesystem state to a robust PostgreSQL database (SQLAlchemy) and Cloudflare R2 (S3-compatible) object storage.

**Architecture:** 
- Use **SQLAlchemy (Async)** to model `Manga`, `Chapter`, and `Page` tables.
- Use **Aiobotocore / Boto3** to upload translated images to a public Cloudflare R2 bucket.
- Expose the R2 bucket directly via a custom Cloudflare domain (Option 1).
- Wipe the old `/data` volume and start fresh (No data migration script required).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (Async), asyncpg, Alembic (Migrations), aioboto3 (or boto3), Cloudflare R2.

**Spec:** Backend Database & Storage Overhaul.

## Global Constraints

- Do not use blocking I/O (no sync `open`, no sync `boto3` inside async endpoints without `run_in_threadpool`, prefer `aioboto3` or `httpx`).
- Run `ruff` and `mypy` on all modified python files.
- The Cloudflare R2 bucket must be considered public for reads; backend only needs `upload` credentials.
- Do not make double calls to the translation API to avoid double billing. The system will extract both image and JSON/OCR data efficiently.

---

### Task 1: Environment & Dependency Setup

**Files:**
- Modify: `apps/api/requirements.txt`
- Modify: `.env`
- Modify: `docker-compose.yml`
- Create: `apps/api/alembic.ini` (will be generated)

**Interfaces:**
- Consumes: Existing FastAPI project.
- Produces: Project ready for Database migrations and S3 connections.

- [ ] **Step 1: Install Dependencies**
Modify `apps/api/requirements.txt` to add:
```text
sqlalchemy>=2.0.29
asyncpg>=0.29.0
alembic>=1.13.1
aioboto3>=12.4.0
```

- [ ] **Step 2: Add Environment Variables**
In `.env.example` (or mock values in `.env` if instructed):
```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/ogma

# Cloudflare R2
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=ogma-manga
R2_PUBLIC_URL=https://cdn.yourdomain.com
```

- [ ] **Step 3: Update Docker Compose**
Modify `docker-compose.yml` to include a `postgres` service and set `DATABASE_URL` for `api` and `api-worker`. Remove the old local `ogma_data` volume mappings since we will use R2. (Keep it temporarily if `manga-translator` needs a scratch pad).
```yaml
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=ogma
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

- [ ] **Step 4: Commit**
```bash
git add apps/api/requirements.txt docker-compose.yml
git commit -m "chore: setup postgres and aioboto3 dependencies"
```

---

### Task 2: Database Models & Alembic Migrations

**Files:**
- Create: `apps/api/src/db/database.py`
- Create: `apps/api/src/db/models.py`
- Modify: `apps/api/alembic/env.py`

**Interfaces:**
- Consumes: `DATABASE_URL`.
- Produces: Async session maker and SQLAlchemy declarative models.

- [ ] **Step 1: Database Config**
In `apps/api/src/db/database.py`:
```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ogma")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: Define Models**
In `apps/api/src/db/models.py`:
```python
from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.database import Base
import enum

class TranslationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"

class Manga(Base):
    __tablename__ = "mangas"
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(String, primary_key=True, index=True)
    manga_id = Column(String, ForeignKey("mangas.id"))
    total_pages = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(TranslationStatus), default=TranslationStatus.PENDING)

class Page(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chapter_id = Column(String, ForeignKey("chapters.id"))
    page_index = Column(Integer)
    image_url = Column(String, nullable=True) # Cloudflare R2 URL
    ocr_data = Column(JSON, nullable=True) # Bounding boxes & translations
    status = Column(Enum(TranslationStatus), default=TranslationStatus.PENDING)
```

- [ ] **Step 3: Setup Alembic**
Initialize Alembic (run `alembic init -t async alembic` if not done), configure `alembic/env.py` to import `Base` and `models.py`, and run the first migration `alembic revision --autogenerate -m "init"`.

- [ ] **Step 4: Commit**
```bash
git add apps/api/src/db/
git commit -m "feat: create sqlalchemy async models for manga and pages"
```

---

### Task 3: Cloudflare R2 Storage Service

**Files:**
- Create: `apps/api/src/services/storage.py`

**Interfaces:**
- Consumes: Aiobotocore/aioboto3.
- Produces: Utility to upload image bytes and return the public URL.

- [ ] **Step 1: Implement S3 Upload**
```python
import os
import aioboto3

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "ogma-manga")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

async def upload_image_to_r2(file_bytes: bytes, destination_path: str) -> str:
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto"
    ) as s3:
        await s3.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=destination_path,
            Body=file_bytes,
            ContentType="image/png"
        )
    return f"{R2_PUBLIC_URL}/{destination_path}"
```

- [ ] **Step 2: Commit**
```bash
git add apps/api/src/services/
git commit -m "feat: implement cloudflare r2 async storage service"
```

---

### Task 4: Refactor Worker to Save to DB & Upload to R2

**Files:**
- Modify: `apps/api/src/worker.py`
- Modify: `apps/api/src/main.py`

**Interfaces:**
- Consumes: `storage.py`, `database.py`.
- Produces: Translated images directly uploaded to R2, with database records created instead of local Redis state.

- [ ] **Step 1: Update `process_page` in Worker**
Instead of writing to local disk, the worker will:
1. Receive image bytes.
2. Send to translation API (Optionally, hit the JSON endpoint alongside the image endpoint, or configure the translation API to return multipart data if supported. *For this step, we assume the worker just extracts the PNG first*).
3. Upload to R2: `url = await upload_image_to_r2(translated_bytes, f"{chapter_id}/{page_index}.png")`.
4. Update the DB `Page` status to `DONE` and set `image_url = url`.

- [ ] **Step 2: Update `main.py` Status Polling**
Refactor `/api/manga/{chapter_id}/status` to query the PostgreSQL `Page` table using `session.execute(select(Page).where(Page.chapter_id == chapter_id))` instead of pulling from Redis. Calculate total and completed dynamically.

- [ ] **Step 3: Remove Local File Serving**
Remove `app.mount("/data", StaticFiles(directory="/data"), name="data")` from `main.py` since images are now loaded directly from the Cloudflare CDN.

- [ ] **Step 4: Commit**
```bash
git add apps/api/src/worker.py apps/api/src/main.py
git commit -m "refactor: migrate worker and api to postgres and cloudflare r2"
```
