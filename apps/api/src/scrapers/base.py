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

    @abstractmethod
    async def extract_manga_info(self, url: str) -> MangaPreview:
        """Extracts manga title, cover, and list of chapters from the series page."""

    @abstractmethod
    async def extract_chapter_pages(self, chapter_url: str) -> list[PageItem]:
        """Extracts page images from a specific chapter page."""
