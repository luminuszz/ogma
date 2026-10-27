import base64
import hashlib
import json
import re
from typing import AsyncGenerator
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright

from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem

ORION_CRYPTO_SECRET = "OrionNexus2025CryptoKey!Secure"
NEXUS_CHAPTER_SECRET = "NexusToons2026SecretKeyForChapterEncryption!@#$"


class OrionCrypto:
    """Decrypts AES/XOR/SBox obfuscated payloads used by NexusToons API."""

    def __init__(self, secret: str = ORION_CRYPTO_SECRET) -> None:
        self.keys: list[dict] = []
        for n in range(5):
            seed = f"_orion_key_{n}_v2_{secret}".encode("utf-8")
            digest_bytes = hashlib.sha256(seed).digest()
            sbox = list(range(256))
            j = 0
            for i in range(256):
                j = (j + sbox[i] + digest_bytes[i % len(digest_bytes)]) % 256
                sbox[i], sbox[j] = sbox[j], sbox[i]
            rsbox = [0] * 256
            for i in range(256):
                rsbox[sbox[i]] = i
            self.keys.append({"key": digest_bytes, "sbox": sbox, "rsbox": rsbox})

    @staticmethod
    def rotate_right(val: int, amt: int) -> int:
        amt = amt % 8
        return ((val >> amt) | (val << (8 - amt))) & 0xFF

    def decrypt(self, key_idx: int, b64_text: str) -> str:
        if key_idx < 0 or key_idx >= len(self.keys):
            key_idx = 0
        k = self.keys[key_idx]
        a = k["key"]
        rsbox = k["rsbox"]
        o = list(base64.b64decode(b64_text))
        s = [0] * len(o)
        l = len(a)
        for c in range(len(o) - 1, -1, -1):
            val = o[c]
            prev = o[c - 1] if c > 0 else a[l - 1]
            val ^= prev
            val = rsbox[val]
            rot = ((a[(c + 3) % l] + (c & 0xFF)) & 0xFF) % 7 + 1
            val = self.rotate_right(val, rot)
            val ^= a[c % l]
            s[c] = val
        return bytes(s).decode("utf-8")

    def process_response(self, data: dict | list | str | int | float | bool) -> dict | list | str | int | float | bool:
        if not (isinstance(data, dict) and "d" in data and "v" in data):
            return data
        key_idx = 0 if data.get("v") == 1 else data.get("k", 0)
        decrypted = self.decrypt(key_idx, data["d"])
        return json.loads(decrypted)


class NexusChapterCodec:
    """Encodes and decodes chapter tokens used in NexusToons /r/{token} URLs."""

    @staticmethod
    def _xor(text: str, key: str) -> str:
        return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(text))

    @staticmethod
    def _b64url_decode(s: str) -> str:
        s = s.replace("-", "+").replace("_", "/")
        s += "=" * ((4 - len(s) % 4) % 4)
        return base64.b64decode(s).decode("utf-8")

    @classmethod
    def decode_token(cls, token: str) -> dict | None:
        try:
            o = cls._b64url_decode(token)
            parts = o.split("|")
            c = parts[0]
            a = cls._b64url_decode(c)
            l = cls._xor(a, NEXUS_CHAPTER_SECRET).split("|")
            if len(l) < 3:
                return None
            return {"chapterId": int(l[0]), "mangaSlug": l[1] or ""}
        except Exception:
            return None


class NexusToonsProvider(BaseProvider):
    name = "nexustoons"

    def __init__(self) -> None:
        self._crypto = OrionCrypto()
        self._codec = NexusChapterCodec()

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        return "nexustoons.com" in parsed.netloc and (
            "/manga/" in parsed.path
            or "/api/manga/" in parsed.path
            or "/r/" in parsed.path
            or "/api/chapter/" in parsed.path
        )

    def _extract_slug(self, url: str) -> str:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "manga" in parts:
            idx = parts.index("manga")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        elif "r" in parts:
            idx = parts.index("r")
            if idx + 1 < len(parts):
                info = self._codec.decode_token(parts[idx + 1])
                if info and info.get("mangaSlug"):
                    return info["mangaSlug"]
        return ""

    def _extract_chapter_id(self, url: str) -> int | None:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "chapter" in parts:
            idx = parts.index("chapter")
            if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                return int(parts[idx + 1])
        elif "r" in parts:
            idx = parts.index("r")
            if idx + 1 < len(parts):
                info = self._codec.decode_token(parts[idx + 1])
                if info and info.get("chapterId"):
                    return info["chapterId"]
        # Fallback: check trailing digit
        if parts and parts[-1].isdigit():
            return int(parts[-1])
        return None

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://nexustoons.com/",
            "Accept": "application/json, text/plain, */*",
            "Cookie": "nx_ct=2; nexus.birthdate=2000-01-01; contentFilter=basic",
        }

    async def _fetch_json(self, url: str) -> dict | list:
        async with httpx.AsyncClient(
            timeout=30.0, headers=self._get_headers(), follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return self._crypto.process_response(data)

    async def extract_manga_info(self, url: str) -> MangaPreview:
        slug = self._extract_slug(url)
        if not slug:
            raise ValueError(f"Não foi possível identificar o slug da obra na URL: {url}")

        api_url = f"https://nexustoons.com/api/manga/{slug}"
        manga_data = await self._fetch_json(api_url)
        if not isinstance(manga_data, dict):
            raise ValueError(f"Resposta inválida da API do NexusToons para a obra: {slug}")

        title = manga_data.get("title") or slug.replace("-", " ").title()
        cover_url = manga_data.get("coverImage")
        raw_chapters = manga_data.get("chapters", [])

        chapters: list[ChapterItem] = []
        for ch in raw_chapters:
            ch_num = str(ch.get("number", ""))
            ch_id = ch.get("id")
            if not ch_id or not ch_num:
                continue

            item_id = f"{self.name}:{slug}:{ch_num}:{ch_id}"
            item_url = f"https://nexustoons.com/api/chapter/{ch_id}"
            chapter_title = ch.get("title") or f"Capítulo {ch_num}"

            chapters.append(
                ChapterItem(
                    id=item_id,
                    number=ch_num,
                    title=chapter_title,
                    url=item_url,
                )
            )

        def sort_key(item: ChapterItem) -> float:
            try:
                return float(item.number)
            except ValueError:
                return 0.0

        chapters.sort(key=sort_key)

        return MangaPreview(
            provider=self.name,
            manga_id=f"{self.name}:{slug}",
            title=title,
            cover_url=cover_url,
            chapters=chapters,
        )

    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        ch_id = self._extract_chapter_id(chapter_url)
        if not ch_id:
            # If chapter_url is formatted as {name}:{slug}:{num}:{id}
            if ":" in chapter_url:
                parts = chapter_url.split(":")
                if len(parts) >= 4 and parts[3].isdigit():
                    ch_id = int(parts[3])

        if not ch_id:
            raise ValueError(f"Não foi possível identificar o ID do capítulo: {chapter_url}")

        api_url = f"https://nexustoons.com/api/chapter/{ch_id}"
        ch_data = await self._fetch_json(api_url)
        if not isinstance(ch_data, dict):
            raise ValueError(f"Resposta inválida ao obter páginas do capítulo {ch_id}")

        pages_data = ch_data.get("pages", [])
        page_items: list[PageItem] = []
        for i, p in enumerate(pages_data):
            img_url = p.get("imageUrl")
            if img_url:
                page_items.append(PageItem(page_index=i, image_url=img_url))

        return page_items

    async def download_pages(
        self, pages: list[PageItem]
    ) -> AsyncGenerator[tuple[PageItem, bytes], None]:
        headers = self._get_headers()
        async with httpx.AsyncClient(
            timeout=45.0, headers=headers, follow_redirects=True
        ) as client:
            for page in pages:
                success = False
                for attempt in range(3):
                    try:
                        resp = await client.get(page.image_url)
                        if resp.status_code == 200:
                            yield page, resp.content
                            success = True
                            break
                    except Exception:
                        pass

                if not success:
                    # Resilient fallback: use Playwright if HTTP request fails
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
                            context = await browser.new_context(user_agent=headers["User-Agent"])
                            pg = await context.new_page()
                            r = await pg.goto(page.image_url, timeout=30000)
                            if not r or r.status != 200:
                                raise RuntimeError(
                                    f"Falha ao baixar imagem {page.image_url} via Playwright (status {r.status if r else 'None'})"
                                )
                            body = await r.body()
                            yield page, body
                        finally:
                            await browser.close()
