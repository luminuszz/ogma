# Web Scraper Module & Provider Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an extensible web scraper module with provider strategy in Ogma, enabling automated extraction of series metadata, chapters, and chapter images from LycanToons (and future providers) into Cloudflare R2 and PostgreSQL, controllable via a dedicated "Scrapper" modal on the frontend.

**Architecture:** A provider strategy pattern (`BaseProvider`, `ProviderRegistry`, `LycantoonsProvider`) runs on the Python backend (`apps/api`) using Playwright for Cloudflare-bypassing web scraping. Granular chapter scraping jobs are queued in ARQ/Redis and processed asynchronously, uploading page images to Cloudflare R2 and reporting real-time progress via Redis PubSub/SSE. On the frontend (`apps/web`), a "Scrapper" button opens a modal that previews the detected manga and chapters, allowing bulk or selective scraping.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy, ARQ, Redis, Playwright, Cloudflare R2 (`aioboto3`), TypeScript, React 19, Tailwind CSS, TanStack Query, Vitest, Pytest.

**Spec:** [`docs/superpowers/specs/2026-10-21-web-scraper-module-design.md`](file:///home/daviribeiro/projects/personal/ogma/docs/superpowers/specs/2026-10-21-web-scraper-module-design.md)

## Global Constraints

- Backend code must reside under `apps/api/src/`.
- All Git commits must strictly follow Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`).
- Preserves existing database schema (`Manga`, `Chapter`, `Page`) and MangaDex features without regressions.
- LycanToons images bypass machine translation by default since content is already Brazilian Portuguese.
- All tasks must be test-driven (TDD: write failing test, verify failure, implement, verify pass, commit).

---

### Task 1: Scraper Core Models & Base Provider Interface

**Files:**
- Create: `apps/api/src/scrapers/__init__.py`
- Create: `apps/api/src/scrapers/base.py`
- Create: `apps/api/tests/__init__.py`
- Create: `apps/api/tests/test_scrapers_base.py`

**Interfaces:**
- Consumes: `pydantic.BaseModel`, `abc.ABC`, `abc.abstractmethod`
- Produces: `ChapterItem`, `MangaPreview`, `PageItem`, `BaseProvider`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_scrapers_base.py`:
```python
import pytest
from pydantic import ValidationError
from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem


def test_chapter_item_model():
    item = ChapterItem(id="test:1", number="1", title="Chapter 1", url="https://example.com/1")
    assert item.id == "test:1"
    assert item.number == "1"
    assert item.title == "Chapter 1"
    assert item.url == "https://example.com/1"


def test_chapter_item_requires_mandatory_fields():
    with pytest.raises(ValidationError):
        ChapterItem(id="test:1")  # missing number and url


def test_manga_preview_model():
    preview = MangaPreview(
        provider="dummy",
        manga_id="dummy:123",
        title="Test Manga",
        cover_url="https://example.com/cover.jpg",
        chapters=[
            ChapterItem(id="dummy:123:1", number="1", url="https://example.com/1")
        ]
    )
    assert preview.provider == "dummy"
    assert len(preview.chapters) == 1


def test_page_item_model():
    page = PageItem(page_index=0, image_url="https://example.com/page-0000.jpg")
    assert page.page_index == 0
    assert page.image_url == "https://example.com/page-0000.jpg"


def test_base_provider_subclass_must_implement_abstract_methods():
    class IncompleteProvider(BaseProvider):
        name = "incomplete"

    with pytest.raises(TypeError):
        IncompleteProvider()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
./venv/bin/pytest apps/api/tests/test_scrapers_base.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'src.scrapers.base'`

- [ ] **Step 3: Write minimal implementation**

Create `apps/api/src/scrapers/__init__.py` (empty file).
Create `apps/api/src/scrapers/base.py`:
```python
from abc import ABC, abstractmethod
from pydantic import BaseModel


class ChapterItem(BaseModel):
    id: str
    number: str
    title: str | None = None
    url: str


class MangaPreview(BaseModel):
    provider: str
    manga_id: str
    title: str
    cover_url: str | None = None
    chapters: list[ChapterItem]


class PageItem(BaseModel):
    page_index: int
    image_url: str


class BaseProvider(ABC):
    name: str

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Determines if this provider can handle the given URL."""
        pass

    @abstractmethod
    async def extract_manga_info(self, url: str) -> MangaPreview:
        """Extracts manga title, cover, and list of chapters from the series page."""
        pass

    @abstractmethod
    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        """Extracts page images from a specific chapter page."""
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_base.py -v
```
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/scrapers/ apps/api/tests/
git commit -m "feat: add scraper base models and provider interface"
```

---

### Task 2: Provider Registry & Resolution

**Files:**
- Create: `apps/api/src/scrapers/registry.py`
- Create: `apps/api/tests/test_scrapers_registry.py`

**Interfaces:**
- Consumes: `BaseProvider`, `MangaPreview`, `PageItem` from `src.scrapers.base`
- Produces: `ProviderRegistry`, `get_registry()`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_scrapers_registry.py`:
```python
import pytest
from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem
from src.scrapers.registry import ProviderRegistry


class MockProvider(BaseProvider):
    name = "mock_provider"

    def can_handle(self, url: str) -> bool:
        return "mocksite.com" in url

    async def extract_manga_info(self, url: str) -> MangaPreview:
        return MangaPreview(
            provider="mock_provider",
            manga_id="mock:1",
            title="Mock Title",
            chapters=[]
        )

    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        return []


def test_registry_register_and_get():
    registry = ProviderRegistry()
    provider = MockProvider()
    registry.register(provider)

    found = registry.get_provider_for_url("https://mocksite.com/series/test")
    assert found is not None
    assert found.name == "mock_provider"


def test_registry_returns_none_for_unsupported_url():
    registry = ProviderRegistry()
    registry.register(MockProvider())

    found = registry.get_provider_for_url("https://unknown-site.org/manga/123")
    assert found is None


def test_registry_list_providers():
    registry = ProviderRegistry()
    registry.register(MockProvider())
    assert registry.list_providers() == ["mock_provider"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_registry.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'src.scrapers.registry'`

- [ ] **Step 3: Write minimal implementation**

Create `apps/api/src/scrapers/registry.py`:
```python
from src.scrapers.base import BaseProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: list[BaseProvider] = []

    def register(self, provider: BaseProvider) -> None:
        self._providers.append(provider)

    def get_provider_for_url(self, url: str) -> BaseProvider | None:
        for provider in self._providers:
            if provider.can_handle(url):
                return provider
        return None

    def list_providers(self) -> list[str]:
        return [p.name for p in self._providers]


_global_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    return _global_registry
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_registry.py -v
```
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/scrapers/registry.py apps/api/tests/test_scrapers_registry.py
git commit -m "feat: add provider registry and url resolver"
```

---

### Task 3: LycanToons Provider Implementation

**Files:**
- Modify: `apps/api/requirements.txt`
- Create: `apps/api/src/scrapers/providers/__init__.py`
- Create: `apps/api/src/scrapers/providers/lycantoons.py`
- Create: `apps/api/tests/test_scrapers_lycantoons.py`

**Interfaces:**
- Consumes: `BaseProvider`, `MangaPreview`, `ChapterItem`, `PageItem` from `src.scrapers.base`
- Produces: `LycantoonsProvider`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_scrapers_lycantoons.py`:
```python
import pytest
from src.scrapers.providers.lycantoons import LycantoonsProvider


def test_lycantoons_can_handle_valid_urls():
    provider = LycantoonsProvider()
    assert provider.can_handle("https://lycantoons.com/series/a-empregada-secreta-do-conde") is True
    assert provider.can_handle("http://lycantoons.com/series/qualquer-obra") is True
    assert provider.can_handle("https://mangadex.org/title/12345") is False
    assert provider.can_handle("https://google.com") is False


def test_lycantoons_extracts_slug():
    provider = LycantoonsProvider()
    slug = provider._extract_slug("https://lycantoons.com/series/a-empregada-secreta-do-conde")
    assert slug == "a-empregada-secreta-do-conde"

    slug2 = provider._extract_slug("https://lycantoons.com/series/a-empregada-secreta-do-conde/10")
    assert slug2 == "a-empregada-secreta-do-conde"


def test_lycantoons_parse_rsc_payload():
    provider = LycantoonsProvider()
    sample_html = '''
    <script>self.__next_f.push([1,"\\"title\\":\\"A Empregada Secreta do Conde\\",\\"capitulos\\":[{\\"id\\":1001,\\"numero\\":2},{\\"id\\":1000,\\"numero\\":1}]"])</script>
    '''
    info = provider._parse_series_data_from_html(sample_html, "a-empregada-secreta-do-conde")
    assert info["title"] == "A Empregada Secreta do Conde"
    assert len(info["chapters"]) == 2
    assert info["chapters"][0]["number"] == "1"
    assert info["chapters"][1]["number"] == "2"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_lycantoons.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'src.scrapers.providers.lycantoons'`

- [ ] **Step 3: Write minimal implementation**

Update `apps/api/requirements.txt`: append `playwright>=1.40.0`.
Create `apps/api/src/scrapers/providers/__init__.py` (empty file).
Create `apps/api/src/scrapers/providers/lycantoons.py`:
```python
import json
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright

from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem


class LycantoonsProvider(BaseProvider):
    name = "lycantoons"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        return "lycantoons.com" in parsed.netloc and "/series/" in parsed.path

    def _extract_slug(self, url: str) -> str:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "series" in parts:
            idx = parts.index("series")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return ""

    def _parse_series_data_from_html(self, html: str, slug: str) -> dict:
        # Extract title
        title_match = re.search(r'\\"title\\":\\"([^\\"]+)\\"', html)
        if not title_match:
            title_match = re.search(r'<title>([^<|]+)', html)
        title = title_match.group(1).strip() if title_match else slug.replace("-", " ").title()

        # Extract cover image
        cover_match = re.search(r'https://cdn\.lycantoons\.com/file/lycantoons/covers/[^\s"\'\\]+', html)
        cover_url = cover_match.group(0) if cover_match else None

        # Extract chapters JSON array from RSC payload
        chapters_data = []
        caps_match = re.search(r'\\"capitulos\\":(\[\{.*?\}\])', html)
        if caps_match:
            try:
                raw_json = caps_match.group(1).replace('\\"', '"')
                parsed_caps = json.loads(raw_json)
                for cap in parsed_caps:
                    num = str(cap.get("numero", ""))
                    cap_id = f"lycantoons:{slug}:{num}"
                    chapters_data.append({
                        "id": cap_id,
                        "number": num,
                        "title": f"Capítulo {num}",
                        "url": f"https://lycantoons.com/series/{slug}/{num}"
                    })
            except Exception:
                pass

        # Sort chapters numerically
        chapters_data.sort(key=lambda x: float(x["number"]) if x["number"].replace(".", "", 1).isdigit() else 0)

        return {
            "title": title,
            "cover_url": cover_url,
            "chapters": chapters_data
        }

    async def extract_manga_info(self, url: str) -> MangaPreview:
        slug = self._extract_slug(url)
        series_url = f"https://lycantoons.com/series/{slug}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.route("**/*", lambda route: route.abort() if any(ad in route.request.url for ad in ["pubadx", "analytics", "ads"]) else route.continue_())
            await page.goto(series_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            html = await page.content()
            await browser.close()

        parsed = self._parse_series_data_from_html(html, slug)
        return MangaPreview(
            provider=self.name,
            manga_id=f"lycantoons:{slug}",
            title=parsed["title"],
            cover_url=parsed["cover_url"],
            chapters=[ChapterItem(**c) for c in parsed["chapters"]]
        )

    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        slug = self._extract_slug(chapter_url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.route("**/*", lambda route: route.abort() if any(ad in route.request.url for ad in ["pubadx", "analytics", "ads"]) else route.continue_())
            await page.goto(chapter_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # Scroll to trigger lazy loading
            for _ in range(12):
                await page.evaluate("window.scrollBy(0, 2500)")
                await page.wait_for_timeout(150)

            image_urls = await page.evaluate(f"""() => {{
                const imgs = Array.from(document.querySelectorAll('img'))
                    .map(i => i.src)
                    .filter(src => src.includes('/file/lycantoons/{slug}/cap-'));
                return Array.from(new Set(imgs));
            }}""")

            await browser.close()

        # Sort pages by index pattern (page-XXXX.jpg)
        image_urls.sort()
        return [PageItem(page_index=i, image_url=url) for i, url in enumerate(image_urls)]
```

Register `LycantoonsProvider` in `apps/api/src/scrapers/registry.py`:
```python
from src.scrapers.providers.lycantoons import LycantoonsProvider

_global_registry.register(LycantoonsProvider())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_lycantoons.py -v
```
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/requirements.txt apps/api/src/scrapers/ apps/api/tests/
git commit -m "feat: implement lycantoons scraper provider"
```

---

### Task 4: API Endpoints for Scraper Preview & Start

**Files:**
- Modify: `apps/api/src/main.py`
- Create: `apps/api/tests/test_scrapers_endpoints.py`

**Interfaces:**
- Consumes: `get_registry` from `src.scrapers.registry`
- Produces: `POST /api/scraper/preview`, `POST /api/scraper/start`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_scrapers_endpoints.py`:
```python
import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_scraper_preview_returns_400_for_unsupported_url():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/scraper/preview", json={"url": "https://unknown.com/series/test"})
        assert response.status_code == 400
        assert "Nenhum provedor suportado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_scraper_preview_missing_url():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/scraper/preview", json={})
        assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_endpoints.py -v
```
Expected: FAIL with 404 Not Found (endpoint does not exist yet).

- [ ] **Step 3: Write minimal implementation**

Add to `apps/api/src/main.py`:
```python
from src.scrapers.registry import get_registry


class ScraperPreviewRequest(BaseModel):
    url: str


class ScraperStartRequest(BaseModel):
    provider: str
    mangaId: str
    title: str
    chapters: list[dict]
    forceTranslate: bool = False


@app.post("/api/scraper/preview")
async def scraper_preview(req: ScraperPreviewRequest):
    registry = get_registry()
    provider = registry.get_provider_for_url(req.url)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail=f"Nenhum provedor suportado para a URL: {req.url}"
        )
    try:
        preview = await provider.extract_manga_info(req.url)
        return {
            "supported": True,
            "provider": preview.provider,
            "mangaId": preview.manga_id,
            "title": preview.title,
            "coverUrl": preview.cover_url,
            "chapters": [c.model_dump() for c in preview.chapters]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao extrair dados da obra: {str(e)}")


@app.post("/api/scraper/start")
async def scraper_start(req: ScraperStartRequest, background_tasks: BackgroundTasks):
    registry = get_registry()
    if req.provider not in registry.list_providers():
        raise HTTPException(status_code=400, detail="Provedor inválido.")

    async with AsyncSessionLocal() as session:
        # 1. Ensure Manga exists
        manga_res = await session.execute(select(Manga).where(Manga.id == req.mangaId))
        manga_obj = manga_res.scalar_one_or_none()
        if not manga_obj:
            manga_obj = Manga(id=req.mangaId, title=req.title)
            session.add(manga_obj)
        else:
            manga_obj.title = req.title

        # 2. Ensure Chapters exist
        for ch in req.chapters:
            ch_res = await session.execute(select(Chapter).where(Chapter.id == ch["id"]))
            chapter_obj = ch_res.scalar_one_or_none()
            if not chapter_obj:
                chapter_obj = Chapter(
                    id=ch["id"],
                    manga_id=req.mangaId,
                    chapter_number=str(ch.get("number", "")),
                    total_pages=0,
                    status=TranslationStatus.PROCESSING,
                )
                session.add(chapter_obj)
            else:
                chapter_obj.status = TranslationStatus.PROCESSING

        await session.commit()

    # 3. Enqueue ARQ jobs
    for ch in req.chapters:
        await redis_pool.enqueue_job(
            "scrape_and_download_chapter",
            req.provider,
            ch["id"],
            ch["url"],
            req.forceTranslate,
            _job_id=f"scrape_{ch['id']}",
        )

    return {"status": "queued", "count": len(req.chapters)}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_endpoints.py -v
```
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/main.py apps/api/tests/test_scrapers_endpoints.py
git commit -m "feat: add scraper preview and start api endpoints"
```

---

### Task 5: ARQ Background Worker Job for Chapter Scraping & R2 Upload

**Files:**
- Modify: `apps/api/src/worker.py`
- Create: `apps/api/tests/test_scrapers_worker.py`

**Interfaces:**
- Consumes: `get_registry` from `src.scrapers.registry`, `upload_image_to_r2` from `src.services.storage`
- Produces: `scrape_and_download_chapter` registered in `WorkerSettings.functions`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_scrapers_worker.py`:
```python
import pytest
from src.worker import WorkerSettings, scrape_and_download_chapter


def test_worker_settings_registers_scraper_job():
    func_names = [f.__name__ for f in WorkerSettings.functions]
    assert "scrape_and_download_chapter" in func_names
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_worker.py -v
```
Expected: FAIL with `AssertionError: assert 'scrape_and_download_chapter' in ['process_page']`

- [ ] **Step 3: Write minimal implementation**

In `apps/api/src/worker.py`:
Add `scrape_and_download_chapter`:
```python
from src.scrapers.registry import get_registry


async def scrape_and_download_chapter(
    ctx, provider_name: str, chapter_id: str, chapter_url: str, force_translate: bool = False
):
    registry = get_registry()
    provider = next((p for p in registry._providers if p.name == provider_name), None)
    if not provider:
        raise ValueError(f"Provider {provider_name} not found.")

    # 1. Extract pages using the provider
    pages = await provider.extract_chapter_pages(chapter_url)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter_obj = result.scalar_one_or_none()
        if chapter_obj:
            chapter_obj.total_pages = len(pages)
            chapter_obj.status = TranslationStatus.PROCESSING

        # Prepare Page records
        for page in pages:
            existing_page = await session.execute(
                select(Page).where(Page.chapter_id == chapter_id, Page.page_index == page.page_index)
            )
            page_obj = existing_page.scalar_one_or_none()
            if not page_obj:
                session.add(Page(chapter_id=chapter_id, page_index=page.page_index, status=TranslationStatus.PENDING))

        await session.commit()

    # 2. Download and upload each image with browser context
    async with httpx.AsyncClient(headers={"referer": "https://lycantoons.com/"}, timeout=60.0) as client:
        for page in pages:
            try:
                resp = await client.get(page.image_url)
                resp.raise_for_status()
                image_bytes = resp.content

                dest_path = f"{chapter_id}/{page.page_index}.png"
                image_url = await upload_image_to_r2(image_bytes, dest_path)

                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        select(Page).where(Page.chapter_id == chapter_id, Page.page_index == page.page_index)
                    )
                    page_record = res.scalar_one_or_none()
                    if page_record:
                        page_record.status = TranslationStatus.DONE
                        page_record.image_url = image_url
                        await session.commit()

                # Publish SSE progress update
                r = await redis.from_url(REDIS_URL)
                await r.publish(f"chapter:{chapter_id}", json.dumps({"page_index": page.page_index, "url": image_url}))
                await r.aclose()

            except Exception as e:
                print(f"Error processing page {page.page_index} for {chapter_id}: {e}")
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        select(Page).where(Page.chapter_id == chapter_id, Page.page_index == page.page_index)
                    )
                    p_rec = res.scalar_one_or_none()
                    if p_rec:
                        p_rec.status = TranslationStatus.ERROR
                        await session.commit()

    # 3. Mark Chapter as DONE
    async with AsyncSessionLocal() as session:
        ch_res = await session.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter_obj = ch_res.scalar_one_or_none()
        if chapter_obj:
            chapter_obj.status = TranslationStatus.DONE
            await session.commit()
```

Add `scrape_and_download_chapter` to `WorkerSettings.functions`:
```python
class WorkerSettings:
    functions: list = [process_page, scrape_and_download_chapter]
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_worker.py -v
```
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/worker.py apps/api/tests/test_scrapers_worker.py
git commit -m "feat: add scrape_and_download_chapter job to arq worker"
```

---

### Task 6: Frontend API Client & Types

**Files:**
- Modify: `apps/web/src/api.ts`
- Create: `apps/web/src/api.scraper.test.ts`

**Interfaces:**
- Consumes: `fetch` API
- Produces: `previewScraper(url: string)`, `startScraper(payload: ScraperStartPayload)`

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/api.scraper.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';

describe('Scraper API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('calls previewScraper with url and returns data', async () => {
    const mockResponse = {
      supported: true,
      provider: 'lycantoons',
      mangaId: 'lycantoons:test',
      title: 'Test Manga',
      chapters: []
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const res = await api.previewScraper('https://lycantoons.com/series/test');
    expect(global.fetch).toHaveBeenCalledWith('/api/scraper/preview', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ url: 'https://lycantoons.com/series/test' })
    }));
    expect(res).toEqual(mockResponse);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pnpm --filter web vitest run src/api.scraper.test.ts
```
Expected: FAIL (`api.previewScraper is not a function`)

- [ ] **Step 3: Write minimal implementation**

In `apps/web/src/api.ts`, add:
```typescript
export interface ScraperChapterItem {
  id: string;
  number: string;
  title?: string;
  url: string;
}

export interface ScraperPreviewResponse {
  supported: boolean;
  provider: string;
  mangaId: string;
  title: string;
  coverUrl?: string;
  chapters: ScraperChapterItem[];
}

export interface ScraperStartPayload {
  provider: string;
  mangaId: string;
  title: string;
  chapters: ScraperChapterItem[];
  forceTranslate?: boolean;
}

// In the api object:
export const api = {
  // ... existing methods ...
  previewScraper: async (url: string): Promise<ScraperPreviewResponse> => {
    const res = await fetch('/api/scraper/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Falha ao buscar prévia da obra');
    }
    return res.json();
  },

  startScraper: async (payload: ScraperStartPayload): Promise<{ status: string; count: number }> => {
    const res = await fetch('/api/scraper/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Falha ao iniciar scraping');
    }
    return res.json();
  },
};
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pnpm --filter web vitest run src/api.scraper.test.ts
```
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/api.ts apps/web/src/api.scraper.test.ts
git commit -m "feat: add scraper methods to frontend api client"
```

---

### Task 7: Frontend Scraper Modal Component

**Files:**
- Create: `apps/web/src/components/ScraperModal.tsx`
- Create: `apps/web/src/components/ScraperModal.test.tsx`

**Interfaces:**
- Consumes: `api.previewScraper`, `api.startScraper` from `@/api`, `Modal` from `@/components/Modal`
- Produces: `ScraperModal` component with `isOpen` and `onClose` props

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/components/ScraperModal.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ScraperModal } from './ScraperModal';

const queryClient = new QueryClient();

describe('ScraperModal', () => {
  it('renders input for url when open', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={() => {}} />
      </QueryClientProvider>
    );

    expect(screen.getByPlaceholderText(/Cole a URL da obra/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pnpm --filter web vitest run src/components/ScraperModal.test.tsx
```
Expected: FAIL (Cannot find module `./ScraperModal`)

- [ ] **Step 3: Write minimal implementation**

Create `apps/web/src/components/ScraperModal.tsx`:
```tsx
import React, { useState } from 'react';
import { Modal } from './Modal';
import { api, ScraperPreviewResponse } from '../api';
import { Loader2, Globe, CheckSquare, Square } from 'lucide-react';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';

interface ScraperModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ScraperModal({ isOpen, onClose }: ScraperModalProps) {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [preview, setPreview] = useState<ScraperPreviewResponse | null>(null);
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());
  const [isStarting, setIsStarting] = useState(false);
  const queryClient = useQueryClient();

  const handleFetchPreview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsLoading(true);
    setPreview(null);
    try {
      const data = await api.previewScraper(url.trim());
      setPreview(data);
      setSelectedChapters(new Set(data.chapters.map(c => c.id)));
    } catch (err: any) {
      toast.error(err.message || 'Erro ao buscar obra.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleSelectAll = () => {
    if (!preview) return;
    if (selectedChapters.size === preview.chapters.length) {
      setSelectedChapters(new Set());
    } else {
      setSelectedChapters(new Set(preview.chapters.map(c => c.id)));
    }
  };

  const handleToggleChapter = (id: string) => {
    const next = new Set(selectedChapters);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedChapters(next);
  };

  const handleStartScraping = async () => {
    if (!preview || selectedChapters.size === 0) return;
    setIsStarting(true);
    try {
      const chaptersToScrape = preview.chapters.filter(c => selectedChapters.has(c.id));
      await api.startScraper({
        provider: preview.provider,
        mangaId: preview.mangaId,
        title: preview.title,
        chapters: chaptersToScrape
      });
      toast.success(`${chaptersToScrape.length} capítulos enfileirados para scraping!`);
      queryClient.invalidateQueries({ queryKey: ['library'] });
      onClose();
      setUrl('');
      setPreview(null);
    } catch (err: any) {
      toast.error(err.message || 'Erro ao iniciar scraping.');
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Web Scraper de Mangás">
      <div className="flex flex-col gap-4">
        <form onSubmit={handleFetchPreview} className="flex gap-2">
          <input
            type="text"
            placeholder="Cole a URL da obra (ex: LycanToons)..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isLoading || isStarting}
            className="flex-1 bg-panel border border-panel-light rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary text-sm"
          />
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="bg-primary hover:bg-primary/90 text-white font-medium px-4 py-2.5 rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50 text-sm shrink-0"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Globe size={16} />}
            Buscar
          </button>
        </form>

        {preview && (
          <div className="flex flex-col gap-4 mt-2">
            <div className="flex gap-4 items-center p-3 bg-panel/30 border border-panel-light rounded-xl">
              {preview.coverUrl && (
                <img src={preview.coverUrl} alt={preview.title} className="w-16 h-24 object-cover rounded-md shrink-0" />
              )}
              <div className="flex flex-col">
                <h4 className="font-bold text-foreground text-lg">{preview.title}</h4>
                <span className="text-xs text-foreground-muted uppercase tracking-wider">
                  Provedor: {preview.provider} • {preview.chapters.length} capítulos encontrados
                </span>
              </div>
            </div>

            <div className="flex justify-between items-center px-1">
              <span className="text-sm text-foreground-muted">
                {selectedChapters.size} de {preview.chapters.length} selecionados
              </span>
              <button
                type="button"
                onClick={handleToggleSelectAll}
                className="text-sm text-primary hover:underline flex items-center gap-1"
              >
                {selectedChapters.size === preview.chapters.length ? (
                  <>
                    <CheckSquare size={16} /> Desmarcar todos
                  </>
                ) : (
                  <>
                    <Square size={16} /> Marcar todos
                  </>
                )}
              </button>
            </div>

            <div className="max-h-60 overflow-y-auto flex flex-col gap-1 border border-panel-light rounded-lg p-2 bg-panel/10">
              {preview.chapters.map((ch) => {
                const isSelected = selectedChapters.has(ch.id);
                return (
                  <div
                    key={ch.id}
                    onClick={() => handleToggleChapter(ch.id)}
                    className="flex items-center gap-3 p-2 hover:bg-panel/40 rounded cursor-pointer transition-colors"
                  >
                    {isSelected ? <CheckSquare size={16} className="text-primary" /> : <Square size={16} className="text-foreground-muted" />}
                    <span className="text-sm font-medium">{ch.title || `Capítulo ${ch.number}`}</span>
                  </div>
                );
              })}
            </div>

            <button
              type="button"
              onClick={handleStartScraping}
              disabled={isStarting || selectedChapters.size === 0}
              className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 shadow-md mt-2"
            >
              {isStarting ? <Loader2 size={18} className="animate-spin" /> : null}
              Iniciar Scraping ({selectedChapters.size} capítulos)
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pnpm --filter web vitest run src/components/ScraperModal.test.tsx
```
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/ScraperModal.tsx apps/web/src/components/ScraperModal.test.tsx
git commit -m "feat: add ScraperModal component with preview and chapter selection"
```

---

### Task 8: Frontend Home Integration (Button "Scrapper" & Trigger Modal)

**Files:**
- Modify: `apps/web/src/pages/Home.tsx`

**Interfaces:**
- Consumes: `ScraperModal` from `@/components/ScraperModal`
- Produces: "Scrapper" button next to "Baixar Novo" in `Home.tsx`

- [ ] **Step 1: Write/Update the failing test**

In `apps/web/src/pages/Home.test.tsx` (create or update):
```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { Home } from './Home';

const queryClient = new QueryClient();

describe('Home page', () => {
  it('renders Scrapper button alongside Baixar Novo', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Home />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.getByRole('button', { name: /scrapper/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /baixar novo/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pnpm --filter web vitest run src/pages/Home.test.tsx
```
Expected: FAIL (button with name /scrapper/i not found)

- [ ] **Step 3: Write minimal implementation**

In `apps/web/src/pages/Home.tsx`:
1. Import `Globe` from `lucide-react`.
2. Import `ScraperModal` from `@/components/ScraperModal`.
3. Add state: `const [isScraperModalOpen, setIsScraperModalOpen] = useState(false);`
4. Add the button next to "Baixar Novo":
```tsx
<div className="flex items-center gap-3">
  <button
    onClick={() => setIsScraperModalOpen(true)}
    className="bg-panel hover:bg-panel-light text-foreground border border-panel-light font-medium py-2 px-5 rounded-full flex items-center justify-center transition-colors shadow-sm shrink-0"
  >
    <Globe size={18} className="mr-2 text-primary" />
    Scrapper
  </button>

  <button
    onClick={() => setIsSearchModalOpen(true)}
    className="bg-primary hover:bg-primary/90 text-white font-medium py-2 px-6 rounded-full flex items-center justify-center transition-colors shadow-lg shrink-0"
  >
    <Plus size={18} className="mr-2" />
    Baixar Novo
  </button>
</div>
```
5. Render `<ScraperModal isOpen={isScraperModalOpen} onClose={() => setIsScraperModalOpen(false)} />`.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pnpm --filter web vitest run src/pages/Home.test.tsx
```
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/Home.tsx apps/web/src/pages/Home.test.tsx
git commit -m "feat: integrate scrapper button and modal trigger on home page"
```

---

### Task 9: End-to-End Verification & Integration Test

**Files:**
- Create: `apps/api/tests/test_scrapers_e2e.py`

**Interfaces:**
- Consumes: All backend and frontend scraper components
- Produces: Complete passing test suite

- [ ] **Step 1: Write E2E integration test**

Create `apps/api/tests/test_scrapers_e2e.py`:
```python
import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_scraper_full_flow_preview_and_start(monkeypatch):
    # Mock LycantoonsProvider.extract_manga_info to avoid real browser launch in test
    from src.scrapers.base import ChapterItem, MangaPreview
    from src.scrapers.providers.lycantoons import LycantoonsProvider

    async def mock_extract(self, url):
        return MangaPreview(
            provider="lycantoons",
            manga_id="lycantoons:mock-series",
            title="Mock Series",
            cover_url="https://example.com/cover.webp",
            chapters=[
                ChapterItem(id="lycantoons:mock-series:1", number="1", title="Capítulo 1", url="https://lycantoons.com/series/mock-series/1")
            ]
        )

    monkeypatch.setattr(LycantoonsProvider, "extract_manga_info", mock_extract)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Preview
        preview_resp = await ac.post("/api/scraper/preview", json={"url": "https://lycantoons.com/series/mock-series"})
        assert preview_resp.status_code == 200
        data = preview_resp.json()
        assert data["title"] == "Mock Series"
        assert len(data["chapters"]) == 1

        # 2. Start
        start_resp = await ac.post("/api/scraper/start", json={
            "provider": "lycantoons",
            "mangaId": data["mangaId"],
            "title": data["title"],
            "chapters": data["chapters"]
        })
        assert start_resp.status_code == 200
        assert start_resp.json()["status"] == "queued"
        assert start_resp.json()["count"] == 1
```

- [ ] **Step 2: Run test to verify it passes**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_e2e.py -v
```
Expected: PASS

- [ ] **Step 3: Run full backend and frontend test suites**

Run:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/ -v
pnpm --filter web vitest run src/api.scraper.test.ts src/components/ScraperModal.test.tsx src/pages/Home.test.tsx
```
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add apps/api/tests/test_scrapers_e2e.py
git commit -m "test: add end-to-end integration test for scraper preview and start"
```
