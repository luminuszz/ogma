from abc import ABC, abstractmethod
from typing import AsyncGenerator

import httpx
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

    @abstractmethod
    async def extract_manga_info(self, url: str) -> MangaPreview:
        """Extracts manga title, cover, and list of chapters from the series page."""

    @abstractmethod
    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        """Extracts page images from a specific chapter page."""

    async def download_page_image(self, image_url: str) -> bytes:
        """Downloads image bytes for a single page. Default uses httpx."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return resp.content

    async def download_pages(
        self, pages: list[PageItem]
    ) -> AsyncGenerator[tuple[PageItem, bytes], None]:
        """Downloads images for a list of pages. Default calls download_page_image."""
        for page in pages:
            data = await self.download_page_image(page.image_url)
            yield page, data
