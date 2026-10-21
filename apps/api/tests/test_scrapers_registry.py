from src.scrapers.base import BaseProvider, MangaPreview, PageItem
from src.scrapers.registry import ProviderRegistry, get_registry


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


def test_get_registry():
    reg = get_registry()
    assert isinstance(reg, ProviderRegistry)
    assert get_registry() is reg
