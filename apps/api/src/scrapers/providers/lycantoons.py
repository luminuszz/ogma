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
