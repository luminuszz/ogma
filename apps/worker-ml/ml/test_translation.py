"""Tests for the translation and typesetting modules."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
import httpx

from ml.translation import translate_text, SYSTEM_PROMPT
from ml.typesetting import render_text_on_image, _word_wrap, _fit_font_size
from ml.vision import BoundingBox


class TestTranslation:
    """Tests for the Ollama translation client."""

    def test_translate_text_success(self):
        """Should call Ollama API and return translated text."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Olá Mundo"}
        mock_response.raise_for_status = MagicMock()

        with patch("ml.translation.httpx.post", return_value=mock_response) as mock_post:
            result = translate_text("Hello World", ollama_url="http://fake:11434")

        assert result == "Olá Mundo"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["prompt"] == "Hello World"
        assert call_args[1]["json"]["system"] == SYSTEM_PROMPT

    def test_translate_empty_text(self):
        """Should return empty string for empty input without calling API."""
        with patch("ml.translation.httpx.post") as mock_post:
            result = translate_text("")

        assert result == ""
        mock_post.assert_not_called()

    def test_translate_text_api_error(self):
        """Should raise when Ollama API returns an error."""
        with patch("ml.translation.httpx.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=MagicMock()
            )

            with pytest.raises(httpx.HTTPStatusError):
                translate_text("Hello")


class TestTypesetting:
    """Tests for the text rendering module."""

    def test_render_text_on_image(self):
        """Should render text onto an image without crashing."""
        # Create a white image (BGR)
        image = np.ones((200, 300, 3), dtype=np.uint8) * 255

        texts = [
            (BoundingBox(x1=10, y1=10, x2=150, y2=60), "Olá Mundo"),
        ]

        result = render_text_on_image(image, texts)

        assert result.shape == image.shape
        # The result should differ from the original (text was drawn)
        assert not np.array_equal(result, image)

    def test_render_empty_text(self):
        """Should not modify image when text is empty."""
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255

        texts = [
            (BoundingBox(x1=10, y1=10, x2=90, y2=90), ""),
        ]

        result = render_text_on_image(image, texts)

        assert result.shape == image.shape

    def test_render_multiple_texts(self):
        """Should handle multiple text boxes."""
        image = np.ones((300, 400, 3), dtype=np.uint8) * 255

        texts = [
            (BoundingBox(x1=10, y1=10, x2=190, y2=80), "Primeiro texto"),
            (BoundingBox(x1=200, y1=100, x2=380, y2=180), "Segundo texto"),
        ]

        result = render_text_on_image(image, texts)

        assert result.shape == image.shape
        assert not np.array_equal(result, image)
