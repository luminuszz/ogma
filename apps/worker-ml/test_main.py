import pytest
from fastapi.testclient import TestClient
import os
import numpy as np
from unittest.mock import patch, MagicMock
from pathlib import Path

from main import app
from ml.vision import VisionResult, DetectedText, BoundingBox

client = TestClient(app)


def test_process_page_full_pipeline(tmp_path):
    """Test the full pipeline with mocked ML components."""
    fake_image = np.ones((100, 200, 3), dtype=np.uint8) * 255
    fake_vision_result = VisionResult(
        inpainted_image=fake_image,
        detected_texts=[
            DetectedText(
                bbox=BoundingBox(x1=10, y1=10, x2=90, y2=50),
                text="Hello",
                confidence=0.95,
            )
        ],
    )

    with patch("main.DATA_DIR", tmp_path), \
         patch("main.httpx.stream") as mock_stream, \
         patch("ml.vision.run_vision_pipeline", return_value=fake_vision_result), \
         patch("main.get_detector", return_value=MagicMock()), \
         patch("main.get_extractor", return_value=MagicMock()), \
         patch("ml.translation.translate_text", return_value="Olá"):

        mock_ctx = MagicMock()
        mock_stream.return_value = mock_ctx
        mock_response = MagicMock()
        mock_ctx.__enter__.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = [b"fake_image"]

        response = client.post("/process-page", json={
            "url": "http://example.com/page.png",
            "chapterId": "ch123",
            "pageId": "pg1",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "ch123" in data["path"]


def test_process_page_path_traversal(tmp_path):
    """Path traversal should be blocked."""
    with patch("main.DATA_DIR", tmp_path):
        response = client.post("/process-page", json={
            "url": "http://example.com/image.png",
            "chapterId": "../ch123",
            "pageId": "pg456",
        })

        assert response.status_code == 400
        assert "Invalid chapterId or pageId" in response.json()["detail"]


def test_process_page_ml_failure_fallback(tmp_path):
    """When ML pipeline fails, should fallback to raw image."""
    with patch("main.DATA_DIR", tmp_path), \
         patch("main.httpx.stream") as mock_stream, \
         patch("ml.vision.run_vision_pipeline", side_effect=RuntimeError("GPU OOM")), \
         patch("main.get_detector", return_value=MagicMock()), \
         patch("main.get_extractor", return_value=MagicMock()):

        mock_ctx = MagicMock()
        mock_stream.return_value = mock_ctx
        mock_response = MagicMock()
        mock_ctx.__enter__.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = [b"raw_image"]

        response = client.post("/process-page", json={
            "url": "http://example.com/page.png",
            "chapterId": "ch999",
            "pageId": "pg1",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok_no_ml"
