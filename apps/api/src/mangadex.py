import httpx

async def fetch_manga_feed(manga_id: str) -> list[dict]:
    url = f"https://api.mangadex.org/manga/{manga_id}/feed"
    params = {
        "order[chapter]": "desc",
        "limit": 100,
        "translatedLanguage[]": ["en", "pt-br", "pt", "es-la", "es"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
    return [
        {
            "id": item["id"],
            "chapter": item["attributes"].get("chapter"),
            "title": item["attributes"].get("title"),
            "language": item["attributes"].get("translatedLanguage"),
        }
        for item in data.get("data", [])
    ]

async def fetch_chapter_pages(chapter_id: str) -> list[dict]:
    url = f"https://api.mangadex.org/at-home/server/{chapter_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
    base_url = data["baseUrl"]
    chapter_hash = data["chapter"]["hash"]
    
    return [
        {
            "url": f"{base_url}/data/{chapter_hash}/{filename}",
            "pageIndex": i,
            "filename": filename
        }
        for i, filename in enumerate(data["chapter"]["data"])
    ]
