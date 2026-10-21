import pytest
from pydantic import ValidationError
from src.scrapers.base import BaseProvider, ChapterItem, MangaPreview, PageItem


def test_chapter_item_model():
    item = ChapterItem(
        id="test:1", number="1", title="Chapter 1", url="https://example.com/1"
    )
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
        ],
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
