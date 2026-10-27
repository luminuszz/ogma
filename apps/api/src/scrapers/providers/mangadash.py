import base64
import html as html_lib
import re
from typing import AsyncGenerator
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright

from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem


class MangadashProvider(BaseProvider):
    name = "mangadash"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        return "mangadash.net" in parsed.netloc and (
            "/manga/" in parsed.path or "/capitulo/" in parsed.path
        )

    def _extract_slug(self, url: str) -> str:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "manga" in parts:
            idx = parts.index("manga")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        elif "capitulo" in parts:
            idx = parts.index("capitulo")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return ""

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://mangadash.net/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    async def _fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=30.0, headers=self._get_headers(), follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    def _parse_title(self, html: str, slug: str) -> str:
        h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
        if h1_match:
            return html_lib.unescape(h1_match.group(1).strip())
        og_match = re.search(
            r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if og_match:
            title = og_match.group(1).split(" - ")[0].strip()
            if title:
                return html_lib.unescape(title)
        return html_lib.unescape(slug.replace("-", " ").title())

    def _parse_cover(self, html: str) -> str | None:
        og_match = re.search(
            r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if og_match:
            return og_match.group(1).strip()
        return None

    def _parse_chapters(self, html: str, slug: str) -> list[ChapterItem]:
        pattern = re.compile(
            r'<a\s+href="(/capitulo/'
            + re.escape(slug)
            + r'/([^"]+))"[^>]*data-chapter-number="([^"]+)"',
            re.IGNORECASE,
        )
        found: dict[str, ChapterItem] = {}
        for match in pattern.finditer(html):
            rel_url, _, ch_num = match.groups()
            ch_id = f"{self.name}:{slug}:{ch_num}"
            if ch_id not in found:
                full_url = f"https://mangadash.net{rel_url}"
                found[ch_id] = ChapterItem(
                    id=ch_id,
                    number=ch_num,
                    title=f"Capítulo {ch_num}",
                    url=full_url,
                )

        def sort_key(item: ChapterItem) -> float:
            try:
                return float(item.number)
            except ValueError:
                return 0.0

        return sorted(found.values(), key=sort_key)

    async def extract_manga_info(self, url: str) -> MangaPreview:
        slug = self._extract_slug(url)
        if not slug:
            raise ValueError(f"Não foi possível identificar o slug da obra na URL: {url}")

        series_url = f"https://mangadash.net/manga/{slug}"
        html = await self._fetch_html(series_url)

        title = self._parse_title(html, slug)
        cover_url = self._parse_cover(html)
        chapters = self._parse_chapters(html, slug)

        return MangaPreview(
            provider=self.name,
            manga_id=f"{self.name}:{slug}",
            title=title,
            cover_url=cover_url,
            chapters=chapters,
        )

    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            try:
                context = await browser.new_context(user_agent=self._get_headers()["User-Agent"])
                page = await context.new_page()
                await page.route(
                    "**/*",
                    lambda route: (
                        route.abort()
                        if any(
                            ad in route.request.url
                            for ad in [
                                "googletagmanager",
                                "google-analytics",
                                "waust.at",
                                "pubadx",
                                "ads",
                            ]
                        )
                        else route.continue_()
                    ),
                )
                await page.goto(chapter_url, wait_until="domcontentloaded", timeout=60000)

                num_pages = await page.evaluate(
                    """async () => {
                        for (let i = 0; i < 50; i++) {
                            if (window.pdfjsLib && window.pdfUrl) break;
                            await new Promise(r => setTimeout(r, 100));
                        }
                        if (window.pdfjsLib && window.pdfUrl) {
                            const doc = await window.pdfjsLib.getDocument({ url: window.pdfUrl }).promise;
                            return doc.numPages;
                        }
                        const imgs = Array.from(document.querySelectorAll('img'))
                            .filter(img => img.src && (img.src.includes('/storage/mangas/') || img.closest('#pdfContainer')));
                        return imgs.length;
                    }"""
                )

                if not num_pages or num_pages <= 0:
                    raise RuntimeError(f"Nenhuma página encontrada para o capítulo {chapter_url}")

                return [
                    PageItem(page_index=i, image_url=f"{chapter_url}#page={i + 1}")
                    for i in range(num_pages)
                ]
            finally:
                await browser.close()

    async def download_pages(
        self, pages: list[PageItem]
    ) -> AsyncGenerator[tuple[PageItem, bytes], None]:
        if not pages:
            return

        chapter_url = pages[0].image_url.split("#page=")[0]

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            try:
                context = await browser.new_context(user_agent=self._get_headers()["User-Agent"])
                page = await context.new_page()
                await page.route(
                    "**/*",
                    lambda route: (
                        route.abort()
                        if any(
                            ad in route.request.url
                            for ad in [
                                "googletagmanager",
                                "google-analytics",
                                "waust.at",
                                "pubadx",
                                "ads",
                            ]
                        )
                        else route.continue_()
                    ),
                )
                await page.goto(chapter_url, wait_until="domcontentloaded", timeout=60000)

                for p_item in pages:
                    if "#page=" in p_item.image_url:
                        page_num = int(p_item.image_url.split("#page=")[1])
                    else:
                        page_num = p_item.page_index + 1

                    data_url = await page.evaluate(
                        """async (pageNum) => {
                            if (!window.pdfDoc) {
                                if (!window.pdfjsLib || !window.pdfUrl) {
                                    for (let i = 0; i < 50; i++) {
                                        if (window.pdfjsLib && window.pdfUrl) break;
                                        await new Promise(r => setTimeout(r, 100));
                                    }
                                }
                                window.pdfDoc = await window.pdfjsLib.getDocument({ url: window.pdfUrl }).promise;
                            }
                            const pdfPage = await window.pdfDoc.getPage(pageNum);
                            const viewport = pdfPage.getViewport({ scale: 1.0 });
                            const canvas = document.createElement('canvas');
                            canvas.width = viewport.width;
                            canvas.height = viewport.height;
                            const ctx = canvas.getContext('2d');
                            await pdfPage.render({ canvasContext: ctx, viewport: viewport }).promise;
                            return canvas.toDataURL('image/png');
                        }""",
                        page_num,
                    )

                    b64_data = data_url.split(",")[1]
                    raw_bytes = base64.b64decode(b64_data)
                    yield p_item, raw_bytes
            finally:
                await browser.close()
