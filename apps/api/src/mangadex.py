import httpx


async def fetch_manga_feed(manga_id: str) -> list[dict]:
    url = f"https://api.mangadex.org/manga/{manga_id}/feed"
    params = {
        "order[chapter]": "desc",
        "limit": 100,
        "translatedLanguage[]": ["en", "pt-br", "pt", "es-la", "es"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)  # type: ignore
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

async def fetch_chapter_metadata(chapter_id: str) -> dict:
    url = f"https://api.mangadex.org/chapter/{chapter_id}?includes[]=manga"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            return {"manga_id": chapter_id, "title": "Unknown Title", "chapter": "N/A"}
        data = response.json()
        
    attrs = data.get("data", {}).get("attributes", {})
    chapter_number = attrs.get("chapter") or "N/A"
    
    # Extract Manga Title from relationships
    manga_id = chapter_id
    manga_title = "Unknown Title"
    for rel in data.get("data", {}).get("relationships", []):
        if rel.get("type") == "manga":
            manga_id = rel.get("id")
            manga_title = rel.get("attributes", {}).get("title", {}).get("en") or "Unknown Title"
            break
            
    return {
        "manga_id": manga_id,
        "title": manga_title,
        "chapter": chapter_number
    }
