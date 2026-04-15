from pathlib import Path
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "static" / "inputs"
OUTPUT_DIR = BASE_DIR / "static" / "outputs"


class StorageError(Exception):
    pass


def _next_unique_jpg_path(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    while True:
        candidate = directory / f"{uuid4().hex}.jpg"
        if not candidate.exists():
            return candidate


def save_input(file) -> str:
    try:
        file.file.seek(0)
        data = file.file.read()
    except Exception as exc:  # pragma: no cover - depends on runtime upload stream
        raise StorageError("Unable to read uploaded file.") from exc

    if not data:
        raise StorageError("Uploaded file is empty.")

    destination = _next_unique_jpg_path(INPUT_DIR)
    try:
        destination.write_bytes(data)
    except OSError as exc:
        raise StorageError("Failed to save uploaded image.") from exc

    return str(destination)


def save_output(image_bytes: bytes) -> str:
    if not image_bytes:
        raise StorageError("Generated image bytes are empty.")

    destination = _next_unique_jpg_path(OUTPUT_DIR)
    try:
        destination.write_bytes(image_bytes)
    except OSError as exc:
        raise StorageError("Failed to save generated image.") from exc

    return str(destination)
