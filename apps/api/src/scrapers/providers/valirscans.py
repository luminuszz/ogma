import html as html_lib
import re
from urllib.parse import urlparse

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
                return html_lib.unescape(title)
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
        if h1_match:
            return html_lib.unescape(h1_match.group(1).strip())
        return html_lib.unescape(default.replace("-", " ").title())

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

        parsed = urlparse(url)
        series_type = "comic"
        parts = [p for p in parsed.path.split("/") if p]
        if "series" in parts:
            idx = parts.index("series")
            if idx + 1 < len(parts) and parts[idx + 1] in ("comic", "novel"):
                series_type = parts[idx + 1]

        base_url = f"https://valirscans.org/series/{series_type}/{slug}"
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
        # Matches media.valirscans.org images. Prioritize full page content images (/p-...)
        # to avoid capturing sliced fragment strips (/f-...)
        p_urls = re.findall(
            r'https://media\.valirscans\.org/[^"\'\s>]+/p-[^"\'\s>]+\.(?:webp|jpg|jpeg|png)',
            html,
        )
        if p_urls:
            unique_urls = list(dict.fromkeys(p_urls))
        else:
            all_urls = re.findall(
                r'https://media\.valirscans\.org/[^"\'\s>]+\.(?:webp|jpg|jpeg|png)',
                html,
            )
            unique_urls = list(dict.fromkeys(all_urls))

        pages = [
            PageItem(page_index=i + 1, image_url=img_url)
            for i, img_url in enumerate(unique_urls)
        ]
        return pages

    async def download_page_image(self, image_url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0, headers=self._get_headers()) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return resp.content
