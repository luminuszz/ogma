"""Tests for the vision pipeline with mocked ML models."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
import cv2
import tempfile
from pathlib import Path

from ml.vision import (
    BoundingBox,
    DetectedText,
    VisionResult,
    create_text_mask,
    inpaint_image,
    run_vision_pipeline,
)


class FakeDetector:
    """Mock balloon detector that returns predefined boxes."""
    def __init__(self, boxes: list[BoundingBox]):
        self.boxes = boxes

    def detect(self, image: np.ndarray) -> list[BoundingBox]:
        return self.boxes


class FakeExtractor:
    """Mock text extractor that returns predefined text."""
    def __init__(self, texts: dict[tuple[int, int, int, int], tuple[str, float]]):
        self.texts = texts

    def extract(self, image: np.ndarray, bbox: BoundingBox) -> tuple[str, float]:
        key = (bbox.x1, bbox.y1, bbox.x2, bbox.y2)
        return self.texts.get(key, ("", 0.0))


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    """Creates a temporary test image."""
    img = np.ones((200, 300, 3), dtype=np.uint8) * 255  # white image
    # Draw some fake "text" (black rectangles)
    cv2.rectangle(img, (10, 10), (100, 50), (0, 0, 0), -1)
    cv2.rectangle(img, (150, 100), (280, 150), (0, 0, 0), -1)

    path = tmp_path / "test_page.png"
    cv2.imwrite(str(path), img)
    return path


def test_create_text_mask():
    """Mask should cover the bounding box regions."""
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    boxes = [BoundingBox(x1=10, y1=10, x2=50, y2=50)]

    mask = create_text_mask(image, boxes)

    assert mask.shape == (100, 100)
    assert mask[30, 30] == 255  # inside box
    assert mask[0, 0] == 0     # outside box


def test_inpaint_image():
    """Inpainted image should differ from original where mask is applied."""
    image = np.ones((100, 100, 3), dtype=np.uint8) * 128
    # Draw a black rectangle to simulate text
    cv2.rectangle(image, (20, 20), (60, 60), (0, 0, 0), -1)

    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(mask, (20, 20), (60, 60), 255, -1)

    result = inpaint_image(image, mask)

    assert result.shape == image.shape
    # The inpainted area should not be pure black anymore
    inpainted_region = result[30:50, 30:50]
    assert np.mean(inpainted_region) > 10  # not pure black


def test_run_vision_pipeline(sample_image_path: Path):
    """Full pipeline should detect text, extract it, and inpaint."""
    boxes = [
        BoundingBox(x1=10, y1=10, x2=100, y2=50),
        BoundingBox(x1=150, y1=100, x2=280, y2=150),
    ]
    texts = {
        (10, 10, 100, 50): ("Hello World", 0.95),
        (150, 100, 280, 150): ("Goodbye", 0.88),
    }

    detector = FakeDetector(boxes)
    extractor = FakeExtractor(texts)

    result = run_vision_pipeline(sample_image_path, detector, extractor)

    assert isinstance(result, VisionResult)
    assert len(result.detected_texts) == 2
    assert result.detected_texts[0].text == "Hello World"
    assert result.detected_texts[0].confidence == 0.95
    assert result.detected_texts[1].text == "Goodbye"
    assert result.inpainted_image is not None
    assert result.inpainted_image.shape[0] == 200
    assert result.inpainted_image.shape[1] == 300


def test_run_vision_pipeline_no_text(sample_image_path: Path):
    """Pipeline should handle pages with no detected text gracefully."""
    detector = FakeDetector(boxes=[])
    extractor = FakeExtractor(texts={})

    result = run_vision_pipeline(sample_image_path, detector, extractor)

    assert len(result.detected_texts) == 0
    assert result.inpainted_image is not None


def test_run_vision_pipeline_invalid_image(tmp_path: Path):
    """Pipeline should raise ValueError for unreadable images."""
    bad_path = tmp_path / "nonexistent.png"

    detector = FakeDetector(boxes=[])
    extractor = FakeExtractor(texts={})

    with pytest.raises(ValueError, match="Could not load image"):
        run_vision_pipeline(bad_path, detector, extractor)
