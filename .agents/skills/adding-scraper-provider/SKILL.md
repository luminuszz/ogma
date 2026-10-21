---
name: adding-scraper-provider
description: Use when adding a new manga, manhwa, comic, or webtoon scraper provider to the Ogma backend, implementing BaseProvider, or handling Cloudflare WAF and dynamic JavaScript-heavy sites
---

# Adding a Scraper Provider

## Overview

Ogma uses the **Provider Strategy** pattern to extract manga and webtoon series from external websites. Each site is implemented as a standalone subclass of `BaseProvider` that handles metadata extraction, chapter listing, and image downloading while integrating with the ARQ background worker and Cloudflare R2 storage.

## Architecture Map

```
apps/api/src/
├── scrapers/
│   ├── base.py                   # Data models (ChapterItem, PageItem, MangaPreview) & BaseProvider ABC
│   ├── registry.py               # ProviderRegistry for URL matching and provider lookup
│   └── providers/
│       ├── lycantoons.py         # Reference implementation (Next.js RSC + Playwright bypass)
│       └── <new_provider>.py     # Your new provider implementation
├── main.py                       # REST API endpoints (/api/scraper/preview, /api/scraper/start, /retry)
└── worker.py                     # ARQ worker task (scrape_and_download_chapter)
```

## Step-by-Step Implementation

### Step 1: Implement the Provider Class

Create `apps/api/src/scrapers/providers/<provider_name>.py` extending `BaseProvider`:

```python
import re
from typing import AsyncGenerator
from urllib.parse import urlparse
from playwright.async_api import async_playwright

from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem


class ExampleProvider(BaseProvider):
    name = "example"

    def can_handle(self, url: str) -> bool:
        """Return True if the URL belongs to this provider."""
        parsed = urlparse(url)
        return "example.com" in parsed.netloc and "/series/" in parsed.path

    def _extract_slug(self, url: str) -> str:
        """Helper to extract the unique series/manga slug from the URL."""
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "series" in parts:
            idx = parts.index("series")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return ""

    async def extract_manga_info(self, url: str) -> MangaPreview:
        """Extract title, cover image URL, and list of chapters from the series page."""
        slug = self._extract_slug(url)
        series_url = f"https://example.com/series/{slug}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                # Block ads and analytics to speed up load time
                await page.route("**/*", lambda route: route.abort() if any(ad in route.request.url for ad in ["pubadx", "analytics", "ads"]) else route.continue_())
                await page.goto(series_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                html = await page.content()
            finally:
                await browser.close()

        # Parse title and chapters from HTML or embedded JSON payloads
        title = self._parse_title(html, slug)
        chapters_data = self._parse_chapters(html, slug)

        return MangaPreview(
            provider=self.name,
            manga_id=f"{self.name}:{slug}",
            title=title,
            cover_url=self._parse_cover(html),
            chapters=[
                ChapterItem(
                    id=f"{self.name}:{slug}:{c['number']}",
                    number=str(c["number"]),
                    title=c.get("title"),
                    url=c["url"],
                )
                for c in chapters_data
            ],
        )

    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        """Extract all image URLs for a chapter."""
        pages_found: list[str] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                await page.route("**/*", lambda route: route.abort() if any(ad in route.request.url for ad in ["pubadx", "analytics", "ads"]) else route.continue_())

                # Listen to internal API responses triggered during hydration
                async def handle_response(response):
                    if "pages" in response.url and response.status == 200:
                        try:
                            data = await response.json()
                            if isinstance(data, dict) and "pages" in data and isinstance(data["pages"], list):
                                pages_found.extend(data["pages"])
                        except Exception:
                            pass

                page.on("response", handle_response)
                await page.goto(chapter_url, wait_until="domcontentloaded", timeout=30000)

                # Wait for API event or fallback to DOM query
                for _ in range(30):
                    if pages_found:
                        break
                    await page.wait_for_timeout(100)

                # Fallback: query DOM if no API was intercepted
                if not pages_found:
                    slug = self._extract_slug(chapter_url)
                    imgs = await page.evaluate(f"""() => {{
                        return Array.from(document.querySelectorAll('img'))
                            .map(i => i.src)
                            .filter(src => src.includes('/file/{slug}/'));
                    }}""")
                    pages_found.extend(imgs)
            finally:
                await browser.close()

        clean_pages = sorted(list(dict.fromkeys(pages_found)))
        return [PageItem(page_index=i, image_url=url) for i, url in enumerate(clean_pages)]

    async def download_pages(
        self, pages: list[PageItem]
    ) -> AsyncGenerator[tuple[PageItem, bytes], None]:
        """Download images bypassing CDN anti-bot protections."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                for p_item in pages:
                    resp = await page.goto(p_item.image_url, timeout=30000)
                    if not resp or resp.status != 200:
                        raise RuntimeError(f"Failed to download image {p_item.image_url}: status {resp.status if resp else 'None'}")
                    body = await resp.body()
                    yield p_item, body
            finally:
                await browser.close()
```

### Step 2: Register in `registry.py`

In `apps/api/src/scrapers/registry.py`:

```python
from src.scrapers.providers.example import ExampleProvider

_global_registry.register(ExampleProvider())
```

### Step 3: Support Retries in `main.py`

In `apps/api/src/main.py` inside `retry_chapter`:

Ensure URL reconstruction handles the new provider:

```python
if provider_name == "example" and len(parts) >= 3:
    slug, num = parts[1], parts[2]
    ch_url = f"https://example.com/series/{slug}/{num}"
```

---

## Critical Real-World Lessons & Gotchas

### 1. Cloudflare WAF & Anti-Bot Protection (TLS Fingerprinting)
- **Problem**: Python HTTP clients (`httpx`, `requests`, `aiohttp`) use Python's OpenSSL TLS stack. Cloudflare CDN endpoints inspect JA3/JA4 fingerprints and return `403 Forbidden` ("Please enable cookies / you have been blocked") or `429`, even when sending realistic browser `User-Agent` and `Referer` headers.
- **Solution**: Always use **Playwright Chromium** (`page.goto(img_url)`) or a browser context with genuine browser TLS stack to download images from protected CDNs.

### 2. Next.js App Router (RSC) & Client Hydration
- **Problem**: Next.js sites embed chapter and series metadata inside server components (`self.__next_f.push(...)`) or load images through client-side API requests (e.g. `/api/chapters/{id}/view-pages`) rather than static HTML tags. Standard `document.querySelectorAll('img')` returns empty arrays on initial load.
- **Solution**:
  - For series information: parse regex on the RSC payload in the raw HTML string without waiting for client rendering.
  - For chapters: attach `page.on("response", handler)` to intercept the internal API response JSON during page load.

### 3. Playwright Resource Hygiene (Zombie Processes)
- **Problem**: If `page.goto` or script evaluation times out or throws an error before `browser.close()` is reached, headless Chromium instances remain running in the background, eventually exhausting system RAM and file descriptors.
- **Solution**: ALWAYS wrap browser operations inside `try ... finally: await browser.close()`.

### 4. ARQ Queue Deduplication & Retries
- **Problem**: ARQ enforces job deduplication by `_job_id`. If a job failed previously, an `arq:result:{job_id}` key remains in Redis. Subsequent calls to `enqueue_job` with the same `_job_id` return `None` and are silently dropped.
- **Solution**:
  - Always delete `arq:result:{job_id}` prior to calling `enqueue_job`.
  - In `WorkerSettings`, set `retry_on_timeout=True` and `conn_retries=10` to survive idle connection resets on remote Redis servers.

---

## Verification & Testing Guide

Write tests in `apps/api/tests/test_scrapers_<provider_name>.py`:

1. **`test_can_handle`**: Test matching URLs (`True`) and non-matching URLs (`False`).
2. **`test_extract_slug`**: Verify correct slug extraction across various URL formats.
3. **`test_parse_metadata`**: Pass sample HTML/JSON and verify title, chapters, and numbering.
4. **`test_download_pages`**: Mock Playwright and verify image bytes are yielded as `(PageItem, bytes)`.

Run test verification:
```bash
PYTHONPATH=apps/api ./venv/bin/pytest apps/api/tests/test_scrapers_<provider_name>.py -v
```
