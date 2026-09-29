"""
Translation client using local Ollama API (Llama 3 8B).
Translates English comic text to Portuguese with context-aware prompts.
"""

import httpx


OLLAMA_URL_DEFAULT = "http://localhost:11434"
MODEL_DEFAULT = "llama3:8b"

SYSTEM_PROMPT = (
    "You are a professional manga/comic translator. "
    "Translate the following English text to Brazilian Portuguese. "
    "Keep the tone casual, natural, and appropriate for manga dialogue. "
    "Preserve exclamations, onomatopoeia style, and emotional tone. "
    "Return ONLY the translated text, nothing else."
)


def translate_text(
    text: str,
    ollama_url: str = OLLAMA_URL_DEFAULT,
    model: str = MODEL_DEFAULT,
) -> str:
    """Translates English text to Portuguese via local Ollama API."""
    if not text.strip():
        return ""

    response = httpx.post(
        f"{ollama_url}/api/generate",
        json={
            "model": model,
            "prompt": text,
            "system": SYSTEM_PROMPT,
            "stream": False,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()
