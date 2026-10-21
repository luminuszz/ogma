import pytest
from src.scrapers.providers.lycantoons import LycantoonsProvider


def test_lycantoons_can_handle_valid_urls():
    provider = LycantoonsProvider()
    assert provider.can_handle("https://lycantoons.com/series/a-empregada-secreta-do-conde") is True
    assert provider.can_handle("http://lycantoons.com/series/qualquer-obra") is True
    assert provider.can_handle("https://mangadex.org/title/12345") is False
    assert provider.can_handle("https://google.com") is False


def test_lycantoons_extracts_slug():
    provider = LycantoonsProvider()
    slug = provider._extract_slug("https://lycantoons.com/series/a-empregada-secreta-do-conde")
    assert slug == "a-empregada-secreta-do-conde"

    slug2 = provider._extract_slug("https://lycantoons.com/series/a-empregada-secreta-do-conde/10")
    assert slug2 == "a-empregada-secreta-do-conde"


def test_lycantoons_parse_rsc_payload():
    provider = LycantoonsProvider()
    sample_html = '''
    <script>self.__next_f.push([1,"\\"title\\":\\"A Empregada Secreta do Conde\\",\\"capitulos\\":[{\\"id\\":1001,\\"numero\\":2},{\\"id\\":1000,\\"numero\\":1}]"])</script>
    '''
    info = provider._parse_series_data_from_html(sample_html, "a-empregada-secreta-do-conde")
    assert info["title"] == "A Empregada Secreta do Conde"
    assert len(info["chapters"]) == 2
    assert info["chapters"][0]["number"] == "1"
    assert info["chapters"][1]["number"] == "2"
