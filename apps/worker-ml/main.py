from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from pathlib import Path

app = FastAPI()

# Default data directory, can be overridden by tests or environment variable
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))

class ProcessPageRequest(BaseModel):
    url: str
    chapterId: str
    pageId: str

class ProcessPageResponse(BaseModel):
    status: str
    path: str

@app.post("/process-page", response_model=ProcessPageResponse)
def process_page(request: ProcessPageRequest):
    # Determine save path
    chapter_dir = DATA_DIR / request.chapterId
    
    # Create chapter directory if it doesn't exist
    chapter_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = chapter_dir / f"{request.pageId}.png"
    
    # Download the image
    try:
        with httpx.stream("GET", request.url) as response:
            response.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download image: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download image: {str(e)}")
        
    return ProcessPageResponse(
        status="ok",
        path=str(file_path)
    )
