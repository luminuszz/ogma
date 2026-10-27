import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.scrapers.base import PageItem
from src.scrapers.providers.nexustoons import (
    NexusChapterCodec,
    NexusToonsProvider,
    OrionCrypto,
)
from src.scrapers.registry import get_registry


def test_nexustoons_can_handle():
    provider = NexusToonsProvider()
    assert provider.can_handle("https://nexustoons.com/manga/sentido-absoluto-da-espada")
    assert provider.can_handle("https://nexustoons.com/manga/sentido-absoluto-da-espada/")
    assert provider.can_handle("https://nexustoons.com/api/manga/sentido-absoluto-da-espada")
    assert provider.can_handle("https://nexustoons.com/r/ZWxkTFEwcGhFeHdMSFVaWlZsbC1CQUVCQ2hnLUVSWnJDeE51RFJJQUZRRVRPVjhDUTA0U1RWQmVEQk4wWDN3N0J3NUFSRHNLSHg0NGRnWmFjeDhfS1FoU05Rb2NIaUV8YkU5MmVwSHZKbA")
    assert provider.can_handle("https://nexustoons.com/api/chapter/423695")
    assert not provider.can_handle("https://lycantoons.com/series/test")
    assert not provider.can_handle("https://mangadash.net/manga/test")
    assert not provider.can_handle("https://valirscans.org/series/comic/test")


def test_nexustoons_extract_slug():
    provider = NexusToonsProvider()
    assert (
        provider._extract_slug("https://nexustoons.com/manga/sentido-absoluto-da-espada")
        == "sentido-absoluto-da-espada"
    )
    assert (
        provider._extract_slug("https://nexustoons.com/api/manga/sentido-absoluto-da-espada")
        == "sentido-absoluto-da-espada"
    )
    assert provider._extract_slug("https://nexustoons.com/other/path") == ""


def test_nexustoons_codec_and_extract_slug_from_token():
    token = "ZWxkTFEwcGhFeHdMSFVaWlZsbC1CQUVCQ2hnLUVSWnJDeE51RFJJQUZRRVRPVjhDUTA0U1RWQmVEQk4wWDN3N0J3NUFSRHNLSHg0NGRnWmFjeDhfS1FoU05Rb2NIaUV8YkU5MmVwSHZKbA"
    decoded = NexusChapterCodec.decode_token(token)
    assert decoded is not None
    assert decoded["chapterId"] == 423695
    assert decoded["mangaSlug"] == "sentido-absoluto-da-espada"

    provider = NexusToonsProvider()
    assert (
        provider._extract_slug(f"https://nexustoons.com/r/{token}")
        == "sentido-absoluto-da-espada"
    )
    assert provider._extract_chapter_id(f"https://nexustoons.com/r/{token}") == 423695
    assert (
        provider._extract_chapter_id("https://nexustoons.com/api/chapter/423695") == 423695
    )


def test_orion_crypto_passthrough():
    crypto = OrionCrypto()
    # If not enveloped, return as is
    plain_dict = {"title": "Test Title"}
    assert crypto.process_response(plain_dict) == plain_dict


@pytest.mark.asyncio
async def test_nexustoons_extract_manga_info():
    provider = NexusToonsProvider()

    mock_manga_data = {
        "title": "Sentido Absoluto da Espada",
        "coverImage": "https://img.nx-toons.xyz/covers/cover.webp",
        "chapters": [
            {"id": 423695, "number": "207", "title": "Capítulo 207"},
            {"id": 30072, "number": "1", "title": "Capítulo 1"},
            {"id": 35000, "number": "2.5", "title": "Capítulo Especial"},
        ],
    }

    with patch.object(provider, "_fetch_json", new=AsyncMock(return_value=mock_manga_data)):
        preview = await provider.extract_manga_info(
            "https://nexustoons.com/manga/sentido-absoluto-da-espada"
        )

    assert preview.provider == "nexustoons"
    assert preview.manga_id == "nexustoons:sentido-absoluto-da-espada"
    assert preview.title == "Sentido Absoluto da Espada"
    assert preview.cover_url == "https://img.nx-toons.xyz/covers/cover.webp"
    assert len(preview.chapters) == 3

    # Check numerical sorting: 1, 2.5, 207
    assert preview.chapters[0].number == "1"
    assert preview.chapters[0].id == "nexustoons:sentido-absoluto-da-espada:1:30072"
    assert preview.chapters[0].url == "https://nexustoons.com/api/chapter/30072"

    assert preview.chapters[1].number == "2.5"
    assert preview.chapters[1].id == "nexustoons:sentido-absoluto-da-espada:2.5:35000"

    assert preview.chapters[2].number == "207"
    assert preview.chapters[2].id == "nexustoons:sentido-absoluto-da-espada:207:423695"


@pytest.mark.asyncio
async def test_nexustoons_extract_chapter_pages():
    provider = NexusToonsProvider()

    mock_chapter_data = {
        "pages": [
            {"imageUrl": "https://img.nx-toons.xyz/page1.webp", "pageNumber": 1},
            {"imageUrl": "https://img.nx-toons.xyz/page2.webp", "pageNumber": 2},
        ]
    }

    with patch.object(provider, "_fetch_json", new=AsyncMock(return_value=mock_chapter_data)):
        pages = await provider.extract_chapter_pages(
            "https://nexustoons.com/api/chapter/423695"
        )

    assert len(pages) == 2
    assert pages[0].page_index == 0
    assert pages[0].image_url == "https://img.nx-toons.xyz/page1.webp"
    assert pages[1].page_index == 1
    assert pages[1].image_url == "https://img.nx-toons.xyz/page2.webp"


@pytest.mark.asyncio
async def test_nexustoons_download_pages():
    provider = NexusToonsProvider()
    pages = [
        PageItem(page_index=0, image_url="https://img.nx-toons.xyz/page0.webp"),
        PageItem(page_index=1, image_url="https://img.nx-toons.xyz/page1.webp"),
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake-webp-image-bytes"

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        results = []
        async for page, image_bytes in provider.download_pages(pages):
            results.append((page.page_index, image_bytes))

    assert len(results) == 2
    assert results[0] == (0, b"fake-webp-image-bytes")
    assert results[1] == (1, b"fake-webp-image-bytes")


def test_nexustoons_registry():
    registry = get_registry()
    provider = registry.get_provider("nexustoons")
    assert provider is not None
    assert isinstance(provider, NexusToonsProvider)

    url_provider = registry.get_provider_for_url(
        "https://nexustoons.com/manga/sentido-absoluto-da-espada"
    )
    assert url_provider is not None
    assert url_provider.name == "nexustoons"
