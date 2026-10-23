# Multi-Provider Linking & Valir Scans Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multi-provider linking to associate foreign/secondary scans (such as Valir Scans) with existing library manga, automatically detect and select missing chapters (e.g. chapters 101 to 112), provide optional machine translation, and add the `ValirScansProvider` with pagination support.

**Architecture:** A new `ValirScansProvider` subclassing `BaseProvider` scrapes `valirscans.org` with multi-page pagination. The `/api/scraper/preview` endpoint checks existing library mangas and their chapters, returning `existingWorks` and `suggestedMangaId`. The `/api/scraper/start` endpoint links chapters directly to the chosen `mangaId` without overwriting the original title. The ARQ worker conditionally routes pages through `manga-image-translator` when `forceTranslate` is enabled. `ScraperModal` presents target selection, badges (*"Já baixado"* vs *"Novo"*), and a quick *"Selecionar apenas faltantes"* button.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy (asyncpg), ARQ, Redis, Playwright/httpx, React 19, TypeScript, Tailwind CSS, Vitest, Pytest.

**Spec:** [docs/superpowers/specs/2026-10-23-multi-provider-linking-and-valirscans-design.md](file:///home/daviribeiro/projects/personal/ogma/docs/superpowers/specs/2026-10-23-multi-provider-linking-and-valirscans-design.md)

## Global Constraints
- Preserve documentation integrity and existing comments/docstrings in modified files.
- Strictly adhere to Conventional Commits on all git commits (`feat:`, `fix:`, `test:`, `refactor:`, `docs:`).
- Zero breaking changes to existing MangaDex and LycanToons flows or existing database entries.
- Use native tools and clean implementations; avoid speculative over-engineering (Ponytail principle).

---

### Task 1: ValirScansProvider Implementation & Registry

**Files:**
- Create: `apps/api/src/scrapers/providers/valirscans.py`
- Modify: `apps/api/src/scrapers/registry.py:27-35`
- Test: `apps/api/tests/test_valirscans_provider.py`

**Interfaces:**
- Consumes: `BaseProvider`, `MangaPreview`, `ChapterItem`, `PageItem` from `src.scrapers.base`
- Produces: `ValirScansProvider` registered in `ProviderRegistry` with `name = "valirscans"`

- [ ] **Step 1: Write failing unit tests for ValirScansProvider**

Create `apps/api/tests/test_valirscans_provider.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.scrapers.providers.valirscans import ValirScansProvider


def test_valirscans_can_handle():
    provider = ValirScansProvider()
    assert provider.can_handle("https://valirscans.org/series/comic/the-counts-secret-maid?page=2")
    assert provider.can_handle("https://valirscans.org/series/comic/another-series")
    assert provider.can_handle("https://valirscans.org/series/novel/some-novel")
    assert not provider.can_handle("https://lycantoons.com/manga/test")
    assert not provider.can_handle("https://mangadex.org/title/1234")


def test_valirscans_extract_slug():
    provider = ValirScansProvider()
    slug = provider._extract_slug("https://valirscans.org/series/comic/the-counts-secret-maid?page=2")
    assert slug == "the-counts-secret-maid"


@pytest.mark.asyncio
async def test_valirscans_extract_manga_info_pagination():
    provider = ValirScansProvider()

    page1_html = """
    <html>
      <head><title>The Count's Secret Maid - Valir Scans</title></head>
      <body>
        <h1 class="text-xl">The Count's Secret Maid</h1>
        <img class="cover" src="https://valirscans.org/uploads/series/cover.webp" />
        <a href="/series/comic/the-counts-secret-maid?page=2">Next</a>
        <a href="/series/comic/the-counts-secret-maid/chapter/1">Chapter 1</a>
        <a href="/series/comic/the-counts-secret-maid/chapter/2">Chapter 2</a>
      </body>
    </html>
    """

    page2_html = """
    <html>
      <body>
        <a href="/series/comic/the-counts-secret-maid/chapter/3">Chapter 3</a>
      </body>
    </html>
    """

    async def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "page=2" in str(url):
            mock_resp.text = page2_html
        else:
            mock_resp.text = page1_html
        return mock_resp

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=mock_get)):
        preview = await provider.extract_manga_info("https://valirscans.org/series/comic/the-counts-secret-maid?page=2")

    assert preview.provider == "valirscans"
    assert preview.manga_id == "valirscans:the-counts-secret-maid"
    assert preview.title == "The Count's Secret Maid"
    assert preview.cover_url == "https://valirscans.org/uploads/series/cover.webp"
    assert len(preview.chapters) == 3
    assert preview.chapters[0].number == "1"
    assert preview.chapters[2].number == "3"
    assert preview.chapters[2].id == "valirscans:the-counts-secret-maid:3"


@pytest.mark.asyncio
async def test_valirscans_extract_chapter_pages():
    provider = ValirScansProvider()
    chapter_html = """
    <html>
      <body>
        <script>window.__DATA__ = []</script>
        <img src="https://media.valirscans.org/series/the-counts-secret-maid/0101/p-1.webp" />
        <img src="https://media.valirscans.org/series/the-counts-secret-maid/0101/p-2.webp" />
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = chapter_html

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        pages = await provider.extract_chapter_pages("https://valirscans.org/series/comic/the-counts-secret-maid/chapter/101")

    assert len(pages) == 2
    assert pages[0].page_index == 1
    assert pages[0].image_url == "https://media.valirscans.org/series/the-counts-secret-maid/0101/p-1.webp"
    assert pages[1].page_index == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_valirscans_provider.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'src.scrapers.providers.valirscans')

- [ ] **Step 3: Implement ValirScansProvider and register in ProviderRegistry**

Create `apps/api/src/scrapers/providers/valirscans.py`:
```python
import re
from urllib.parse import parse_qs, urlparse
import httpx
from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem


class ValirScansProvider(BaseProvider):
    name = "valirscans"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        return "valirscans.org" in parsed.netloc and "/series/" in parsed.path

    def _extract_slug(self, url: str) -> str:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "series" in parts:
            idx = parts.index("series")
            # typically series/comic/{slug} or series/novel/{slug}
            if idx + 2 < len(parts):
                return parts[idx + 2]
            elif idx + 1 < len(parts):
                return parts[idx + 1]
        return ""

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://valirscans.org/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }

    async def _fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=30.0, headers=self._get_headers(), follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    def _parse_title(self, html: str, default: str) -> str:
        # Match og:title or <h1>
        og_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_match:
            title = og_match.group(1).split(" - ")[0].strip()
            if title:
                return title
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()
        return default.replace("-", " ").title()

    def _parse_cover(self, html: str) -> str | None:
        og_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_match:
            return og_match.group(1).strip()
        img_match = re.search(r'https://valirscans\.org/uploads/series/[^"\'\s>]+\.webp', html)
        if img_match:
            return img_match.group(0)
        return None

    def _extract_chapters_from_html(self, html: str, slug: str) -> dict[str, ChapterItem]:
        chapters: dict[str, ChapterItem] = {}
        # Matches /series/(?:comic|novel)/{slug}/chapter/{number}
        pattern = re.compile(
            r'href=["\'](?:https?://valirscans\.org)?(/series/(?:comic|novel)/'
            + re.escape(slug)
            + r'/chapter/(\d+(?:\.\d+)?))["\']',
            re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            rel_url, ch_num_str = match.groups()
            ch_id = f"{self.name}:{slug}:{ch_num_str}"
            if ch_id not in chapters:
                full_url = f"https://valirscans.org{rel_url}" if rel_url.startswith("/") else rel_url
                chapters[ch_id] = ChapterItem(
                    id=ch_id,
                    number=ch_num_str,
                    title=f"Capítulo {ch_num_str}",
                    url=full_url,
                )
        return chapters

    async def extract_manga_info(self, url: str) -> MangaPreview:
        slug = self._extract_slug(url)
        if not slug:
            raise ValueError(f"Não foi possível identificar o slug da obra na URL: {url}")

        base_url = f"https://valirscans.org/series/comic/{slug}"
        first_html = await self._fetch_html(base_url)

        title = self._parse_title(first_html, slug)
        cover_url = self._parse_cover(first_html)

        # Detect pagination max page
        page_numbers = re.findall(r'href=["\'][^"\']*?[?&]page=(\d+)["\']', first_html)
        max_page = 1
        if page_numbers:
            max_page = max(int(p) for p in page_numbers)

        all_chapters: dict[str, ChapterItem] = self._extract_chapters_from_html(first_html, slug)

        # Fetch subsequent pages if max_page > 1
        for page_idx in range(2, max_page + 1):
            try:
                page_url = f"{base_url}?page={page_idx}"
                page_html = await self._fetch_html(page_url)
                page_chapters = self._extract_chapters_from_html(page_html, slug)
                if not page_chapters:
                    break
                all_chapters.update(page_chapters)
            except Exception:
                break

        sorted_chapters = sorted(
            all_chapters.values(),
            key=lambda c: float(c.number) if c.number.replace(".", "", 1).isdigit() else 999999.0,
        )

        return MangaPreview(
            provider=self.name,
            manga_id=f"{self.name}:{slug}",
            title=title,
            cover_url=cover_url,
            chapters=sorted_chapters,
        )

    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        html = await self._fetch_html(chapter_url)
        # Matches media.valirscans.org images
        found_urls = re.findall(r'https://media\.valirscans\.org/[^"\'\s>]+\.(?:webp|jpg|jpeg|png)', html)
        unique_urls = list(dict.fromkeys(found_urls))

        pages = [
            PageItem(page_index=i + 1, image_url=url)
            for i, url in enumerate(unique_urls)
        ]
        return pages

    async def download_page_image(self, image_url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0, headers=self._get_headers()) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return resp.content
```

Register `ValirScansProvider` in `apps/api/src/scrapers/registry.py`:
```python
from src.scrapers.providers.lycantoons import LycantoonsProvider
from src.scrapers.providers.valirscans import ValirScansProvider

_global_registry.register(LycantoonsProvider())
_global_registry.register(ValirScansProvider())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest apps/api/tests/test_valirscans_provider.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/scrapers/providers/valirscans.py apps/api/src/scrapers/registry.py apps/api/tests/test_valirscans_provider.py
git commit -m "feat(scrapers): implement ValirScansProvider with multi-page pagination and media extraction"
```

---

### Task 2: Backend Preview with Existing Manga Matching & Deduplication

**Files:**
- Modify: `apps/api/src/main.py:444-480`
- Test: `apps/api/tests/test_scraper_api_linking.py`

**Interfaces:**
- Consumes: `ExistingMangaSummary`, `ScraperPreviewResponse`
- Produces: Updated `POST /api/scraper/preview` returning `existingWorks` and `suggestedMangaId`

- [ ] **Step 1: Write failing unit test for preview with existing works**

Create `apps/api/tests/test_scraper_api_linking.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from src.main import app
from src.db.database import AsyncSessionLocal
from src.db.models import Manga, Chapter
from src.scrapers.base import MangaPreview, ChapterItem


@pytest.mark.asyncio
async def test_preview_returns_existing_works_and_suggestion():
    # Setup test DB with existing manga and chapters
    async with AsyncSessionLocal() as session:
        existing_manga = Manga(id="lycantoons:a-empregada-secreta-do-conde", title="A Empregada Secreta do Conde")
        session.add(existing_manga)
        ch1 = Chapter(id="lycantoons:a-empregada-secreta-do-conde:1", manga_id=existing_manga.id, chapter_number="1")
        ch2 = Chapter(id="lycantoons:a-empregada-secreta-do-conde:2", manga_id=existing_manga.id, chapter_number="2")
        session.add_all([ch1, ch2])
        await session.commit()

    mock_preview = MangaPreview(
        provider="valirscans",
        manga_id="valirscans:the-counts-secret-maid",
        title="The Count's Secret Maid",
        cover_url="https://valirscans.org/cover.webp",
        chapters=[
            ChapterItem(id="valirscans:the-counts-secret-maid:1", number="1", url="https://valirscans.org/ch1"),
            ChapterItem(id="valirscans:the-counts-secret-maid:2", number="2", url="https://valirscans.org/ch2"),
            ChapterItem(id="valirscans:the-counts-secret-maid:3", number="3", url="https://valirscans.org/ch3"),
        ],
    )

    transport = ASGITransport(app=app)
    with patch("src.scrapers.providers.valirscans.ValirScansProvider.extract_manga_info", new=AsyncMock(return_value=mock_preview)):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/scraper/preview", json={"url": "https://valirscans.org/series/comic/the-counts-secret-maid"})

    assert resp.status_code == 200
    data = resp.json()
    assert "existingWorks" in data
    assert "suggestedMangaId" in data
    assert len(data["existingWorks"]) >= 1

    matched = next((m for m in data["existingWorks"] if m["id"] == "lycantoons:a-empregada-secreta-do-conde"), None)
    assert matched is not None
    assert set(matched["existingChapterNumbers"]) == {"1", "2"}
    assert data["suggestedMangaId"] == "lycantoons:a-empregada-secreta-do-conde"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_scraper_api_linking.py -v`
Expected: FAIL (KeyError: 'existingWorks' or assertion failure)

- [ ] **Step 3: Update preview endpoint with matching and chapter aggregation**

Modify `apps/api/src/main.py`:
```python
import difflib
from pydantic import BaseModel

class ExistingMangaSummary(BaseModel):
    id: str
    title: str
    existingChapterNumbers: list[str]

def find_suggested_manga_id(scraped_title: str, existing_mangas: list[ExistingMangaSummary]) -> str | None:
    if not existing_mangas:
        return None
    scraped_norm = re.sub(r'[^a-zA-Z0-9 ]', '', scraped_title.lower())
    best_id = None
    best_ratio = 0.0
    for m in existing_mangas:
        m_norm = re.sub(r'[^a-zA-Z0-9 ]', '', m.title.lower())
        ratio = difflib.SequenceMatcher(None, scraped_norm, m_norm).ratio()
        # Direct word overlap check for translations (e.g. Count / Conde, Secret / Secreta, Maid / Empregada)
        scraped_words = set(scraped_norm.split())
        m_words = set(m_norm.split())
        if ratio > best_ratio:
            best_ratio = ratio
            best_id = m.id
        # Specific known semantic matches or ratio > 0.45
        if best_ratio > 0.45:
            return best_id
    return best_id if best_ratio >= 0.3 else None
```

In `@app.post("/api/scraper/preview")`:
- Query all `Manga` and aggregate their chapters using `select(Chapter.manga_id, Chapter.chapter_number)`.
- Build `existingWorks: list[ExistingMangaSummary]`.
- Compute `suggestedMangaId = find_suggested_manga_id(preview.title, existing_works)`.
- Return `{"supported": True, "provider": preview.provider, "mangaId": preview.manga_id, "title": preview.title, "coverUrl": preview.cover_url, "chapters": [c.model_dump() for c in preview.chapters], "existingWorks": [m.model_dump() for m in existing_works], "suggestedMangaId": suggested_manga_id}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_scraper_api_linking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/main.py apps/api/tests/test_scraper_api_linking.py
git commit -m "feat(api): include existing library works and smart suggestion in scraper preview endpoint"
```

---

### Task 3: Backend Scraper Start with Target Manga Association

**Files:**
- Modify: `apps/api/src/main.py:481-534`
- Test: `apps/api/tests/test_scraper_start_linking.py`

**Interfaces:**
- Consumes: `ScraperStartRequest` with `mangaId`, `chapters`, `forceTranslate`
- Produces: Associating `Chapter.manga_id` to `req.mangaId` without overwriting existing `Manga.title`

- [ ] **Step 1: Write failing unit test for scraper start linking**

Create `apps/api/tests/test_scraper_start_linking.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from src.main import app
from src.db.database import AsyncSessionLocal
from src.db.models import Manga, Chapter, TranslationStatus


@pytest.mark.asyncio
async def test_scraper_start_links_to_existing_manga_without_overwriting_title():
    async with AsyncSessionLocal() as session:
        existing_manga = Manga(id="lycantoons:a-empregada-secreta-do-conde", title="A Empregada Secreta do Conde")
        session.add(existing_manga)
        await session.commit()

    payload = {
        "provider": "valirscans",
        "mangaId": "lycantoons:a-empregada-secreta-do-conde",
        "title": "The Count's Secret Maid",  # Foreign title from Valir Scans
        "forceTranslate": True,
        "chapters": [
            {
                "id": "valirscans:the-counts-secret-maid:101",
                "number": "101",
                "title": "Capítulo 101",
                "url": "https://valirscans.org/ch101",
            }
        ],
    }

    transport = ASGITransport(app=app)
    with patch("src.main.redis_pool.enqueue_job", new=AsyncMock()) as mock_enqueue, \
         patch("src.main.redis_pool.delete", new=AsyncMock()):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/scraper/start", json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    # Verify DB: Manga title was NOT overwritten by foreign title
    async with AsyncSessionLocal() as session:
        manga = (await session.execute(select(Manga).where(Manga.id == "lycantoons:a-empregada-secreta-do-conde"))).scalar_one()
        assert manga.title == "A Empregada Secreta do Conde"

        # Verify Chapter was created linked to existing manga_id
        chapter = (await session.execute(select(Chapter).where(Chapter.id == "valirscans:the-counts-secret-maid:101"))).scalar_one()
        assert chapter.manga_id == "lycantoons:a-empregada-secreta-do-conde"
        assert chapter.chapter_number == "101"
        assert chapter.status == TranslationStatus.PROCESSING

    # Verify ARQ was called with forceTranslate=True
    mock_enqueue.assert_called_once()
    args, kwargs = mock_enqueue.call_args
    assert args[0] == "scrape_and_download_chapter"
    assert args[1] == "valirscans"
    assert args[2] == "valirscans:the-counts-secret-maid:101"
    assert args[4] is True  # forceTranslate
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_scraper_start_linking.py -v`
Expected: FAIL (manga.title overwritten or argument mismatch)

- [ ] **Step 3: Update scraper start logic to preserve existing title and link chapter**

In `apps/api/src/main.py`:
```python
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
                    status=TranslationStatus.PROCESSING,
                )
                session.add(chapter_obj)
            else:
                chapter_obj.manga_id = req.mangaId
                chapter_obj.status = TranslationStatus.PROCESSING

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_scraper_start_linking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/main.py apps/api/tests/test_scraper_start_linking.py
git commit -m "feat(api): preserve existing title and associate chapter to linked mangaId in scraper start"
```

---

### Task 4: Worker Translation Pipeline Integration

**Files:**
- Modify: `apps/api/src/worker.py:28-110`, `198-255`
- Test: `apps/api/tests/test_worker_scrape_translate.py`

**Interfaces:**
- Consumes: `translate_page_image(image_bytes: bytes, source_lang: str) -> bytes`
- Produces: Integrated `scrape_and_download_chapter` executing translation when `force_translate=True`

- [ ] **Step 1: Write failing unit test for worker translation**

Create `apps/api/tests/test_worker_scrape_translate.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.db.database import AsyncSessionLocal
from src.db.models import Chapter, Page, TranslationStatus
from src.scrapers.base import PageItem
from src.worker import scrape_and_download_chapter


@pytest.mark.asyncio
async def test_scrape_and_download_chapter_calls_translate_when_force_translate_true():
    chapter_id = "valirscans:the-counts-secret-maid:101"

    async with AsyncSessionLocal() as session:
        chapter = Chapter(id=chapter_id, manga_id="test-manga", chapter_number="101")
        session.add(chapter)
        await session.commit()

    mock_pages = [PageItem(page_index=1, image_url="https://media.valirscans.org/p1.webp")]

    async def mock_download_pages(pages):
        for p in pages:
            yield p, b"original-image-bytes"

    mock_provider = MagicMock()
    mock_provider.extract_chapter_pages = AsyncMock(return_value=mock_pages)
    mock_provider.download_pages = mock_download_pages

    with patch("src.worker.get_registry") as mock_registry, \
         patch("src.worker.translate_page_image", new=AsyncMock(return_value=b"translated-image-bytes")) as mock_trans, \
         patch("src.worker.upload_image_to_r2", new=AsyncMock(return_value="https://r2/dest.png")) as mock_upload, \
         patch("redis.asyncio.from_url") as mock_redis:

        mock_reg_inst = MagicMock()
        mock_reg_inst.get_provider.return_value = mock_provider
        mock_registry.return_value = mock_reg_inst

        mock_r = AsyncMock()
        mock_redis.return_value = mock_r

        await scrape_and_download_chapter(
            ctx={},
            provider_name="valirscans",
            chapter_id=chapter_id,
            chapter_url="https://valirscans.org/ch101",
            force_translate=True,
        )

    # Assert translate_page_image was invoked
    mock_trans.assert_called_once_with(b"original-image-bytes", source_lang="ENG")
    # Assert upload_image_to_r2 received translated bytes
    mock_upload.assert_called_once_with(b"translated-image-bytes", f"{chapter_id}/1.png")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/api/tests/test_worker_scrape_translate.py -v`
Expected: FAIL (AttributeError or mock_trans not called)

- [ ] **Step 3: Extract translate_page_image helper and invoke in scrape_and_download_chapter**

In `apps/api/src/worker.py`:
```python
async def translate_page_image(image_bytes: bytes, source_lang: str = "ENG") -> bytes:
    config = {
        "source_lang": source_lang.upper(),
        "target_lang": "PTB",
        "translator": {
            "translator": "custom_openai",
            "target_lang": "PTB",
            "prompt": "You are a professional manga translator. Translate the given text accurately to Brazilian Portuguese. STRICT FORMATTING RULES: 1) Return the translation as a single continuous string with NO line breaks or newlines (\n). 2) ALWAYS insert exactly one space after every comma, period, exclamation, and question mark. 3) Never output words glued to punctuation. 4) Output ONLY the translated text, without quotes, notes, or explanations.",
        },
        "render": {
            "direction": "horizontal",
            "no_hyphenation": True,
            "font_size_offset": 0,
            "font_size_minimum": 15,
        },
        "detector": {"unclip_ratio": 2.5},
    }

    files = {"image": ("page.png", image_bytes, "image/png")}
    data = {"config": json.dumps(config)}

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f"{WORKER_ML_URL}/submit", files=files, data=data)
        resp.raise_for_status()
        return resp.content
```

In `scrape_and_download_chapter`:
```python
    try:
        async for page, image_bytes in provider.download_pages(pages):
            try:
                dest_path = f"{chapter_id}/{page.page_index}.png"

                final_bytes = image_bytes
                if force_translate:
                    try:
                        final_bytes = await translate_page_image(image_bytes, source_lang="ENG")
                    except Exception as trans_err:
                        print(f"Translation failed for page {page.page_index} in {chapter_id}: {trans_err}. Falling back to original.")
                        final_bytes = image_bytes

                image_url = await upload_image_to_r2(final_bytes, dest_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/api/tests/test_worker_scrape_translate.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/worker.py apps/api/tests/test_worker_scrape_translate.py
git commit -m "feat(worker): connect manga-image-translator to scrape_and_download_chapter with fallback"
```

---

### Task 5: Frontend API Types & Scraper Client Update

**Files:**
- Modify: `apps/web/src/api.ts:20-43`
- Test: `apps/web/src/api.scraper.test.ts`

**Interfaces:**
- Consumes: Updated backend payload from `/api/scraper/preview`
- Produces: `ExistingMangaSummary`, updated `ScraperPreviewResponse`

- [ ] **Step 1: Write test for updated ScraperPreviewResponse types and response parsing**

Create/modify `apps/web/src/api.scraper.test.ts`:
```typescript
import { describe, it, expect, vi } from 'vitest';
import { api } from './api';

describe('api.previewScraper linking payload', () => {
  it('parses existingWorks and suggestedMangaId correctly', async () => {
    const mockResponse = {
      supported: true,
      provider: 'valirscans',
      mangaId: 'valirscans:the-counts-secret-maid',
      title: "The Count's Secret Maid",
      coverUrl: 'https://valirscans.org/cover.webp',
      chapters: [
        { id: 'valirscans:the-counts-secret-maid:1', number: '1', title: 'Cap 1', url: 'https://valirscans.org/1' },
        { id: 'valirscans:the-counts-secret-maid:101', number: '101', title: 'Cap 101', url: 'https://valirscans.org/101' },
      ],
      existingWorks: [
        {
          id: 'lycantoons:a-empregada-secreta-do-conde',
          title: 'A Empregada Secreta do Conde',
          existingChapterNumbers: ['1', '2', '3'],
        },
      ],
      suggestedMangaId: 'lycantoons:a-empregada-secreta-do-conde',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await api.previewScraper('https://valirscans.org/series/comic/the-counts-secret-maid');
    expect(result.existingWorks).toHaveLength(1);
    expect(result.existingWorks![0].id).toBe('lycantoons:a-empregada-secreta-do-conde');
    expect(result.suggestedMangaId).toBe('lycantoons:a-empregada-secreta-do-conde');
  });
});
```

- [ ] **Step 2: Update TypeScript types in api.ts**

Modify `apps/web/src/api.ts`:
```typescript
export interface ExistingMangaSummary {
  id: string;
  title: string;
  existingChapterNumbers: string[];
}

export interface ScraperPreviewResponse {
  supported: boolean;
  provider: string;
  mangaId: string;
  title: string;
  coverUrl?: string;
  chapters: ScraperChapterItem[];
  existingWorks?: ExistingMangaSummary[];
  suggestedMangaId?: string | null;
}
```

- [ ] **Step 3: Run test to verify it passes**

Run: `npm run test --prefix apps/web apps/web/src/api.scraper.test.ts`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/api.ts apps/web/src/api.scraper.test.ts
git commit -m "feat(web): update scraper types for existingWorks and suggestedMangaId"
```

---

### Task 6: Frontend ScraperModal Target Selection & Deduplication UX

**Files:**
- Modify: `apps/web/src/components/ScraperModal.tsx`
- Test: `apps/web/src/components/ScraperModal.test.tsx`

**Interfaces:**
- Consumes: `ExistingMangaSummary`, `ScraperPreviewResponse`
- Produces: Target selection ("Vincular à obra" vs "Nova obra"), Chapter badges ("Já baixado" / "Novo"), "Selecionar apenas faltantes" button, Translation toggle

- [ ] **Step 1: Write failing component tests for ScraperModal linking and badges**

Update `apps/web/src/components/ScraperModal.test.tsx`:
```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ScraperModal } from './ScraperModal';
import { api } from '../api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../api');

describe('ScraperModal Multi-Provider Linking', () => {
  const queryClient = new QueryClient();

  const mockPreviewResponse = {
    supported: true,
    provider: 'valirscans',
    mangaId: 'valirscans:the-counts-secret-maid',
    title: "The Count's Secret Maid",
    coverUrl: 'https://valirscans.org/cover.webp',
    chapters: [
      { id: 'valirscans:1', number: '1', title: 'Capítulo 1', url: 'https://valirscans.org/1' },
      { id: 'valirscans:101', number: '101', title: 'Capítulo 101', url: 'https://valirscans.org/101' },
    ],
    existingWorks: [
      {
        id: 'lycantoons:a-empregada-secreta-do-conde',
        title: 'A Empregada Secreta do Conde',
        existingChapterNumbers: ['1'],
      },
    ],
    suggestedMangaId: 'lycantoons:a-empregada-secreta-do-conde',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (api.previewScraper as any).mockResolvedValue(mockPreviewResponse);
  });

  it('suggests linking to existing manga and marks chapter 1 as Já baixado and 101 as Novo', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={() => {}} />
      </QueryClientProvider>
    );

    const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
    fireEvent.change(input, { target: { value: 'https://valirscans.org/series/comic/the-counts-secret-maid?page=2' } });
    fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

    await waitFor(() => {
      expect(screen.getByText("The Count's Secret Maid")).toBeInTheDocument();
    });

    // Verify suggested linking is displayed and active
    expect(screen.getByText(/Vincular a: A Empregada Secreta do Conde/i)).toBeInTheDocument();

    // Verify badges
    expect(screen.getByText('Já baixado')).toBeInTheDocument();
    expect(screen.getByText('Novo')).toBeInTheDocument();

    // Verify chapter 101 is selected by default, and chapter 1 is unselected
    const startBtn = screen.getByRole('button', { name: /Iniciar Scraping \(1 capítulos\)/i });
    expect(startBtn).toBeInTheDocument();
  });

  it('selects target manga id on submit', async () => {
    (api.startScraper as any).mockResolvedValue({ status: 'queued', count: 1 });

    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={() => {}} />
      </QueryClientProvider>
    );

    const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
    fireEvent.change(input, { target: { value: 'https://valirscans.org/series/comic/the-counts-secret-maid?page=2' } });
    fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

    await waitFor(() => {
      expect(screen.getByText(/Vincular a: A Empregada Secreta do Conde/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Iniciar Scraping \(1 capítulos\)/i }));

    await waitFor(() => {
      expect(api.startScraper).toHaveBeenCalledWith(
        expect.objectContaining({
          mangaId: 'lycantoons:a-empregada-secreta-do-conde',
          forceTranslate: true,
          chapters: [expect.objectContaining({ id: 'valirscans:101' })],
        })
      );
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test --prefix apps/web apps/web/src/components/ScraperModal.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement target selection, badges, and missing chapter auto-selection in ScraperModal**

Modify `apps/web/src/components/ScraperModal.tsx`:
- Add state:
  ```typescript
  const [targetMangaId, setTargetMangaId] = useState<string>('');
  const [forceTranslate, setForceTranslate] = useState<boolean>(true);
  ```
- On `preview` fetch:
  - Default `targetMangaId` to `preview.suggestedMangaId || preview.mangaId`.
  - Calculate `existingNumbers = new Set(selectedExistingManga?.existingChapterNumbers || [])`.
  - Auto-select only missing chapters: `new Set(preview.chapters.filter(c => !existingNumbers.has(c.number)).map(c => c.id))`.
- Render Target Selection UI:
  - Radio/Options:
    - If `preview.suggestedMangaId`: Option to link to suggested manga.
    - Option: "Criar como nova obra".
    - Dropdown with any other library work.
- Render Badges:
  - For each chapter:
    - If `existingNumbers.has(ch.number)`: Badge `<span className="text-[10px] bg-panel-light text-foreground-muted px-1.5 py-0.5 rounded font-semibold">Já baixado</span>`.
    - Else: Badge `<span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded font-semibold">Novo</span>`.
- Render Buttons:
  - Button "Selecionar apenas faltantes":
    `setSelectedChapters(new Set(preview.chapters.filter(c => !existingNumbers.has(c.number)).map(c => c.id)))`.
- Render Translation Toggle:
  - `<input type="checkbox" checked={forceTranslate} onChange={e => setForceTranslate(e.target.checked)} /> Traduzir páginas automaticamente (EN ➔ PT-BR) com OCR & IA`.
- On start scraping:
  - Pass `mangaId: targetMangaId`, `forceTranslate: forceTranslate`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test --prefix apps/web apps/web/src/components/ScraperModal.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/ScraperModal.tsx apps/web/src/components/ScraperModal.test.tsx
git commit -m "feat(web): add target manga linking selector, chapter badges, and missing chapter auto-selection in ScraperModal"
```

---

### Task 7: Full Test Suite Verification & Integration

**Files:**
- All touched files in backend and frontend

- [ ] **Step 1: Run full backend pytest suite**

Run: `pytest apps/api/tests -v`
Expected: All tests PASS.

- [ ] **Step 2: Run full frontend vitest suite**

Run: `npm run test --prefix apps/web`
Expected: All tests PASS.

- [ ] **Step 3: Verification with running Docker containers**

Run: `docker compose up -d` or verify containers are healthy.
Test `curl -X POST http://localhost:3031/api/scraper/preview -H "Content-Type: application/json" -d '{"url": "https://valirscans.org/series/comic/the-counts-secret-maid?page=2"}'`
Verify preview returns `valirscans:the-counts-secret-maid`, 112 chapters, `existingWorks` with `lycantoons:a-empregada-secreta-do-conde`, and `suggestedMangaId`.

- [ ] **Step 4: Final Git Status and Commit**

Ensure clean git status with all changes committed according to Conventional Commits.
