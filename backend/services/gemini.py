import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests

from utils.prompt import get_graduation_prompt


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "static" / "inputs"
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiError(Exception):
    pass


class GeminiAPIError(GeminiError):
    pass


class GeminiEmptyResponseError(GeminiError):
    pass


def _normalize_image_model(model: str) -> str:
    remap = {
        "gemini-3.1-flash": "gemini-3.1-flash-image-preview",
        "gemini-2.5-flash": "gemini-2.5-flash-image",
        "gemini-2.5-flash-preview-image": "gemini-2.5-flash-image",
    }
    return remap.get(model.strip(), model.strip())


def _generation_config_for_model(model: str) -> dict[str, Any]:
    config: dict[str, Any] = {
        "responseModalities": ["IMAGE"],
        "imageConfig": {
            "aspectRatio": "1:1",
        },
    }
    if "3.1" in model:
        config["imageConfig"]["imageSize"] = "2K"
    return config


def _mime_type_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "image/jpeg"


def _mime_type_from_bytes(data: bytes, path: Path) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return _mime_type_for(path)


def _image_part(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if not data:
        raise GeminiAPIError(f"Image file is empty: {path}")

    return {
        "inline_data": {
            "mime_type": _mime_type_from_bytes(data, path),
            "data": base64.b64encode(data).decode("utf-8"),
        }
    }


def _reference_paths(user_image_path: Path) -> list[Path]:
    configured_paths = os.getenv("GEMINI_REFERENCE_IMAGES", "").strip()
    paths: list[Path] = []

    if configured_paths:
        for raw in configured_paths.split(","):
            cleaned = raw.strip()
            if not cleaned:
                continue
            candidate = Path(cleaned)
            if not candidate.is_absolute():
                candidate = (BASE_DIR / candidate).resolve()
            paths.append(candidate)
    else:
        for ext in ("jpg", "jpeg", "png", "webp"):
            paths.extend(INPUT_DIR.glob(f"reference*.{ext}"))

        if not paths:
            for ext in ("jpg", "jpeg", "png", "webp"):
                paths.extend(INPUT_DIR.glob(f"*.{ext}"))

    filtered = []
    seen = set()
    user_resolved = user_image_path.resolve()
    for path in paths:
        resolved = path.resolve()
        if resolved == user_resolved:
            continue
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            filtered.append(resolved)

    if not filtered:
        raise GeminiAPIError(
            "No local reference images found. Add files like "
            "`backend/static/inputs/reference1.jpg` or set GEMINI_REFERENCE_IMAGES."
        )

    return filtered


def _extract_image_bytes(payload: dict[str, Any]) -> bytes:
    for candidate in payload.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inline_data") or part.get("inlineData")
            if not inline:
                continue
            encoded = inline.get("data")
            if encoded:
                try:
                    return base64.b64decode(encoded)
                except Exception as exc:  # pragma: no cover - invalid external payload
                    raise GeminiAPIError("Gemini returned invalid image encoding.") from exc

    return b""


def generate_image(image_path: str) -> bytes:
    image_file = Path(image_path)
    if not image_file.exists():
        raise GeminiAPIError(f"Input image does not exist: {image_path}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiAPIError("GEMINI_API_KEY is not set.")

    model = _normalize_image_model(os.getenv("GEMINI_MODEL", DEFAULT_MODEL))
    url = GEMINI_URL_TEMPLATE.format(model=model)

    parts: list[dict[str, Any]] = [{"text": get_graduation_prompt()}, _image_part(image_file)]
    for reference_path in _reference_paths(image_file):
        parts.append(_image_part(reference_path))

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": _generation_config_for_model(model),
    }

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=120,
        )
    except requests.RequestException as exc:
        raise GeminiAPIError(f"Failed to call Gemini API: {exc}") from exc

    if response.status_code >= 400:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text
        raise GeminiAPIError(
            f"Gemini API error ({response.status_code}). {detail}".strip()
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise GeminiAPIError("Gemini returned a non-JSON response.") from exc

    image_bytes = _extract_image_bytes(data)
    if not image_bytes:
        raise GeminiEmptyResponseError("Gemini response did not contain image data.")

    return image_bytes
