import base64
import mimetypes
import os
from pathlib import Path

import requests

from utils.prompt import get_graduation_prompt


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "static" / "inputs"
OPENAI_IMAGE_EDITS_URL = "https://api.openai.com/v1/images/edits"
DEFAULT_MODEL = "gpt-image-1.5"


class ImageGenerationError(Exception):
    pass


class ImageAPIError(ImageGenerationError):
    pass


class ImageEmptyResponseError(ImageGenerationError):
    pass


def _mime_type_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "image/jpeg"


def _reference_paths(user_image_path: Path) -> list[Path]:
    configured_paths = os.getenv("OPENAI_REFERENCE_IMAGES", "").strip()
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
    seen: set[Path] = set()
    user_resolved = user_image_path.resolve()
    for path in paths:
        resolved = path.resolve()
        if resolved == user_resolved:
            continue
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            filtered.append(resolved)

    if not filtered:
        raise ImageAPIError(
            "No local reference images found. Add files like "
            "`backend/static/inputs/reference1.jpg` or set OPENAI_REFERENCE_IMAGES."
        )

    return filtered


def _extract_image_bytes(payload: dict) -> bytes:
    data = payload.get("data", [])
    if not data:
        return b""

    first = data[0] or {}
    b64_image = first.get("b64_json")
    if b64_image:
        try:
            return base64.b64decode(b64_image)
        except Exception as exc:  # pragma: no cover - external payload
            raise ImageAPIError("OpenAI returned invalid base64 image data.") from exc

    image_url = first.get("url")
    if image_url:
        try:
            result = requests.get(image_url, timeout=120)
            result.raise_for_status()
            return result.content
        except requests.RequestException as exc:
            raise ImageAPIError("OpenAI returned image URL but download failed.") from exc

    return b""


def generate_image(image_path: str) -> bytes:
    image_file = Path(image_path)
    if not image_file.exists():
        raise ImageAPIError(f"Input image does not exist: {image_path}")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ImageAPIError("OPENAI_API_KEY is not set.")

    model = os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    prompt = get_graduation_prompt()
    reference_paths = _reference_paths(image_file)

    data = {
        "model": model,
        "prompt": prompt,
    }
    optional_size = os.getenv("OPENAI_IMAGE_SIZE", "").strip()
    optional_quality = os.getenv("OPENAI_IMAGE_QUALITY", "").strip()
    optional_format = os.getenv("OPENAI_IMAGE_FORMAT", "").strip()
    if optional_size:
        data["size"] = optional_size
    if optional_quality:
        data["quality"] = optional_quality
    if optional_format:
        data["output_format"] = optional_format

    files = []
    handles = []
    try:
        ordered_paths = [image_file, *reference_paths]
        for path in ordered_paths:
            handle = open(path, "rb")
            handles.append(handle)
            files.append(("image[]", (path.name, handle, _mime_type_for(path))))

        try:
            response = requests.post(
                OPENAI_IMAGE_EDITS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files=files,
                timeout=180,
            )
        except requests.RequestException as exc:
            raise ImageAPIError(f"Failed to call OpenAI Images API: {exc}") from exc
    finally:
        for handle in handles:
            handle.close()

    if response.status_code >= 400:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text
        raise ImageAPIError(f"OpenAI Images API error ({response.status_code}). {detail}".strip())

    try:
        payload = response.json()
    except ValueError as exc:
        raise ImageAPIError("OpenAI returned a non-JSON response.") from exc

    image_bytes = _extract_image_bytes(payload)
    if not image_bytes:
        raise ImageEmptyResponseError("OpenAI response did not contain image data.")

    return image_bytes
