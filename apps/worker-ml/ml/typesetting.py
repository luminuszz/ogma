"""
Typesetting module for rendering translated text onto manga pages.
Uses Pillow to calculate word-wrap, resize fonts, and draw text
inside the detected balloon bounding boxes.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from ml.vision import BoundingBox


# Default font path (Anime Ace or fallback)
DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/TTF/AnimeAce.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _find_font() -> str | None:
    """Find an available font on the system."""
    for path in DEFAULT_FONT_PATHS:
        if Path(path).exists():
            return path
    return None


def _word_wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Break text into lines that fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines or [text]


def _fit_font_size(
    text: str,
    box_width: int,
    box_height: int,
    font_path: str | None,
    min_size: int = 8,
    max_size: int = 48,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Find the largest font size where text fits in the bounding box."""
    best_font = None
    best_lines: list[str] = [text]

    for size in range(max_size, min_size - 1, -1):
        try:
            if font_path:
                font = ImageFont.truetype(font_path, size)
            else:
                font = ImageFont.load_default(size=size)
        except (OSError, TypeError):
            font = ImageFont.load_default()

        padding = 4
        lines = _word_wrap(text, font, box_width - padding * 2)

        line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
        total_height = line_height * len(lines) + (len(lines) - 1) * 2

        if total_height <= box_height - padding * 2:
            return font, lines

        best_font = font
        best_lines = lines

    return best_font or ImageFont.load_default(), best_lines


def render_text_on_image(
    image: np.ndarray,
    texts: list[tuple[BoundingBox, str]],
    font_path: str | None = None,
) -> np.ndarray:
    """
    Renders translated text onto an inpainted image.

    Args:
        image: The inpainted image (numpy array, BGR from OpenCV).
        texts: List of (bounding_box, translated_text) pairs.
        font_path: Optional path to a .ttf font file.

    Returns:
        Image with text rendered (numpy array, BGR).
    """
    if font_path is None:
        font_path = _find_font()

    # Convert BGR (OpenCV) to RGB (Pillow)
    pil_image = Image.fromarray(image[:, :, ::-1])
    draw = ImageDraw.Draw(pil_image)

    for bbox, text in texts:
        if not text.strip():
            continue

        box_width = bbox.x2 - bbox.x1
        box_height = bbox.y2 - bbox.y1

        font, lines = _fit_font_size(text, box_width, box_height, font_path)

        line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
        total_text_height = line_height * len(lines) + (len(lines) - 1) * 2

        # Center text vertically in the box
        y_start = bbox.y1 + (box_height - total_text_height) // 2

        for i, line in enumerate(lines):
            line_bbox = font.getbbox(line)
            line_width = line_bbox[2] - line_bbox[0]
            x = bbox.x1 + (box_width - line_width) // 2
            y = y_start + i * (line_height + 2)
            draw.text((x, y), line, fill=(0, 0, 0), font=font)

    # Convert back to BGR (OpenCV)
    return np.array(pil_image)[:, :, ::-1]
