import pytest
from fastapi.testclient import TestClient
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# We need to set DATA_DIR before importing main if it's evaluated on module load,
# but main might just use a constant. Let's patch it in the test.
from main import app

client = TestClient(app)

def test_process_page(tmp_path):
    # Patch the DATA_DIR in main to use our tmp_path
    with patch("main.DATA_DIR", tmp_path):
        payload = {
            "url": "http://example.com/image.png",
            "chapterId": "ch123",
            "pageId": "pg456"
        }
        
        # Mock httpx.stream
        with patch("main.httpx.stream") as mock_stream:
            mock_context_manager = MagicMock()
            mock_stream.return_value = mock_context_manager
            
            mock_response = MagicMock()
            mock_context_manager.__enter__.return_value = mock_response
            
            # Mock the methods on the response
            mock_response.raise_for_status.return_value = None
            mock_response.iter_bytes.return_value = [b"fake", b"_", b"image", b"_", b"data"]
            
            response = client.post("/process-page", json=payload)
            
            assert response.status_code == 200
            expected_path = str(tmp_path / "ch123" / "pg456.png")
            assert response.json() == {
                "status": "ok",
                "path": expected_path
            }
            
            # Check if file was written correctly
            saved_file = tmp_path / "ch123" / "pg456.png"
            assert saved_file.exists()
            assert saved_file.read_bytes() == b"fake_image_data"


def test_process_page_path_traversal(tmp_path):
    with patch("main.DATA_DIR", tmp_path):
        payload = {
            "url": "http://example.com/image.png",
            "chapterId": "../ch123",
            "pageId": "pg456"
        }
        
        response = client.post("/process-page", json=payload)
        
        assert response.status_code == 400
        assert "Invalid chapterId or pageId" in response.json()["detail"]
