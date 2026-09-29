from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import cv2
from pathlib import Path

app = FastAPI()

# Default data directory, can be overridden by tests or environment variable
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

# Lazy-loaded ML models (initialized on first use)
_detector = None
_extractor = None


def get_detector():
    global _detector
    if _detector is None:
        from ml.vision import YOLOBalloonDetector
        _detector = YOLOBalloonDetector()
    return _detector


def get_extractor():
    global _extractor
    if _extractor is None:
        from ml.vision import PaddleTextExtractor
        _extractor = PaddleTextExtractor()
    return _extractor


class ProcessPageRequest(BaseModel):
    url: str
    chapterId: str
    pageId: str


class ProcessPageResponse(BaseModel):
    status: str
    path: str


@app.post("/process-page", response_model=ProcessPageResponse)
def process_page(request: ProcessPageRequest):
    # Determine save paths
    chapter_dir = DATA_DIR / request.chapterId
    raw_path = chapter_dir / f"{request.pageId}_raw.png"
    final_path = chapter_dir / f"{request.pageId}.png"

    # Path traversal protection
    try:
        if not raw_path.resolve().is_relative_to(DATA_DIR.resolve()):
            raise HTTPException(status_code=400, detail="Invalid chapterId or pageId")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chapterId or pageId")

    # Create chapter directory if it doesn't exist
    chapter_dir.mkdir(parents=True, exist_ok=True)

    # 1. Download the image
    try:
        with httpx.stream("GET", request.url) as response:
            response.raise_for_status()
            with open(raw_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download image: {str(e)}")

    # 2. Run vision pipeline (detect balloons, OCR, inpaint)
    from ml.vision import run_vision_pipeline
    try:
        result = run_vision_pipeline(str(raw_path), get_detector(), get_extractor())
    except Exception as e:
        # If ML pipeline fails, just save the raw image
        import shutil
        shutil.copy2(raw_path, final_path)
        return ProcessPageResponse(status="ok_no_ml", path=str(final_path))

    # 3. Translate extracted texts
    from ml.translation import translate_text
    translated_pairs = []
    for dt in result.detected_texts:
        try:
            translated = translate_text(dt.text, ollama_url=OLLAMA_URL, model=OLLAMA_MODEL)
            translated_pairs.append((dt.bbox, translated))
        except Exception:
            # If translation fails for a balloon, use original text
            translated_pairs.append((dt.bbox, dt.text))

    # 4. Typeset translated text onto the inpainted image
    from ml.typesetting import render_text_on_image
    final_image = render_text_on_image(result.inpainted_image, translated_pairs)

    # 5. Save final result
    cv2.imwrite(str(final_path), final_image)

    # Clean up raw file
    try:
        raw_path.unlink()
    except OSError:
        pass

    return ProcessPageResponse(status="ok", path=str(final_path))
