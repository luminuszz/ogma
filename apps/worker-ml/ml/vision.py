"""
Computer Vision pipeline for manga page processing.

Stages:
1. Detect text balloons using YOLO
2. Extract text via PaddleOCR
3. Inpaint (remove) old text using OpenCV
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


@dataclass
class BoundingBox:
    """Represents a detected text region."""
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class DetectedText:
    """A text region with its extracted content."""
    bbox: BoundingBox
    text: str
    confidence: float


@dataclass
class VisionResult:
    """Output of the full vision pipeline."""
    inpainted_image: np.ndarray
    detected_texts: list[DetectedText]


class BalloonDetector(Protocol):
    """Protocol for balloon detection backends."""
    def detect(self, image: np.ndarray) -> list[BoundingBox]: ...


class TextExtractor(Protocol):
    """Protocol for OCR backends."""
    def extract(self, image: np.ndarray, bbox: BoundingBox) -> tuple[str, float]: ...


class YOLOBalloonDetector:
    """YOLO-based balloon detector."""

    def __init__(self, model_path: str = "comic-text-detector.pt"):
        from ultralytics import YOLO
        self.model = YOLO(model_path)

    def detect(self, image: np.ndarray) -> list[BoundingBox]:
        results = self.model(image, verbose=False)
        boxes = []
        for result in results:
            for box in result.boxes:
                coords = box.xyxy[0].cpu().numpy().astype(int)
                boxes.append(BoundingBox(
                    x1=int(coords[0]),
                    y1=int(coords[1]),
                    x2=int(coords[2]),
                    y2=int(coords[3]),
                ))
        return boxes


class PaddleTextExtractor:
    """PaddleOCR-based text extractor for western text."""

    def __init__(self, lang: str = "en"):
        from paddleocr import PaddleOCR
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def extract(self, image: np.ndarray, bbox: BoundingBox) -> tuple[str, float]:
        crop = image[bbox.y1:bbox.y2, bbox.x1:bbox.x2]
        if crop.size == 0:
            return ("", 0.0)

        results = self.ocr.ocr(crop, cls=True)
        if not results or not results[0]:
            return ("", 0.0)

        lines = []
        total_conf = 0.0
        count = 0
        for line in results[0]:
            text = line[1][0]
            conf = line[1][1]
            lines.append(text)
            total_conf += conf
            count += 1

        full_text = " ".join(lines)
        avg_conf = total_conf / count if count > 0 else 0.0
        return (full_text, avg_conf)


def create_text_mask(image: np.ndarray, boxes: list[BoundingBox]) -> np.ndarray:
    """Creates a binary mask covering all detected text regions."""
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for box in boxes:
        cv2.rectangle(mask, (box.x1, box.y1), (box.x2, box.y2), 255, -1)
    return mask


def inpaint_image(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Removes text from image using OpenCV inpainting."""
    return cv2.inpaint(image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)


def run_vision_pipeline(
    image_path: str | Path,
    detector: BalloonDetector,
    extractor: TextExtractor,
) -> VisionResult:
    """
    Full vision pipeline:
    1. Load image
    2. Detect text balloons
    3. Extract text from each balloon
    4. Inpaint (remove old text)
    """
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    # 1. Detect balloons
    boxes = detector.detect(image)

    # 2. Extract text from each region
    detected_texts = []
    for box in boxes:
        text, confidence = extractor.extract(image, box)
        if text.strip():
            detected_texts.append(DetectedText(
                bbox=box,
                text=text,
                confidence=confidence,
            ))

    # 3. Create mask and inpaint
    mask = create_text_mask(image, boxes)
    inpainted = inpaint_image(image, mask)

    return VisionResult(
        inpainted_image=inpainted,
        detected_texts=detected_texts,
    )
