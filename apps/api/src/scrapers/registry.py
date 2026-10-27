from src.scrapers.base import BaseProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: list[BaseProvider] = []

    def register(self, provider: BaseProvider) -> None:
        self._providers.append(provider)

    def get_provider(self, name: str) -> BaseProvider | None:
        for provider in self._providers:
            if provider.name == name:
                return provider
        return None

    def get_provider_for_url(self, url: str) -> BaseProvider | None:
        for provider in self._providers:
            if provider.can_handle(url):
                return provider
        return None

    def list_providers(self) -> list[str]:
        return [p.name for p in self._providers]


_global_registry = ProviderRegistry()

from src.scrapers.providers.lycantoons import LycantoonsProvider
from src.scrapers.providers.mangadash import MangadashProvider
from src.scrapers.providers.valirscans import ValirScansProvider

_global_registry.register(LycantoonsProvider())
_global_registry.register(ValirScansProvider())
_global_registry.register(MangadashProvider())


def get_registry() -> ProviderRegistry:
    return _global_registry
