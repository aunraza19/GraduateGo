from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from utils.env_loader import load_env_file


BASE_DIR = Path(__file__).resolve().parent
load_env_file(BASE_DIR.parent / ".env", override=True)

from services.openai_image import ImageAPIError, ImageEmptyResponseError, generate_image
from services.qr import QRError, generate_qr
from services.storage import StorageError, save_input, save_output


INPUT_DIR = BASE_DIR / "static" / "inputs"
OUTPUT_DIR = BASE_DIR / "static" / "outputs"
FRONTEND_FILE = BASE_DIR / "static" / "index.html"

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def _looks_like_image(data: bytes) -> bool:
    signatures = (
        data.startswith(b"\xff\xd8\xff"),  # JPEG
        data.startswith(b"\x89PNG\r\n\x1a\n"),  # PNG
        data.startswith(b"RIFF") and data[8:12] == b"WEBP",  # WEBP
    )
    return any(signatures)


def _error(status_code: int, message: str, detail: str | None = None) -> JSONResponse:
    payload = {"error": message}
    if detail:
        payload["detail"] = detail
    return JSONResponse(status_code=status_code, content=payload)


app = FastAPI(title="AI Graduation Booth Backend")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static/inputs", StaticFiles(directory=str(INPUT_DIR)), name="static-inputs")
app.mount("/static/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="static-outputs")


@app.get("/")
async def frontend():
    if not FRONTEND_FILE.exists():
        return _error(500, "Frontend missing", "backend/static/index.html not found.")
    return FileResponse(str(FRONTEND_FILE))


@app.post("/generate")
async def generate(file: UploadFile = File(...)):
    if not file or not file.filename:
        return _error(400, "Invalid image upload", "No file provided.")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return _error(
            400,
            "Invalid image upload",
            "Only JPEG, PNG, and WEBP uploads are supported.",
        )

    upload_bytes = await file.read()
    if not upload_bytes or not _looks_like_image(upload_bytes):
        return _error(400, "Invalid image upload", "Uploaded file is not a valid image.")

    try:
        file.file.seek(0)
        input_path = save_input(file)
        generated_bytes = generate_image(input_path)
        output_path = save_output(generated_bytes)
        qr_path = generate_qr(output_path)
    except ImageEmptyResponseError as exc:
        return _error(502, "Empty response from OpenAI", str(exc))
    except ImageAPIError as exc:
        return _error(502, "OpenAI API failure", str(exc))
    except StorageError as exc:
        return _error(500, "File write error", str(exc))
    except QRError as exc:
        return _error(500, "QR generation failure", str(exc))
    except Exception as exc:  # pragma: no cover - safety net
        return _error(500, "Unexpected server error", str(exc))

    return {
        "image_url": f"/static/outputs/{Path(output_path).name}",
        "qr_url": f"/static/outputs/{Path(qr_path).name}",
    }
