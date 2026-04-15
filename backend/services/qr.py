import os
import socket
from pathlib import Path

import qrcode


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "static" / "outputs"


class QRError(Exception):
    pass


def _local_ip() -> str:
    manual_ip = os.getenv("LOCAL_IP", "").strip()
    if manual_ip and not manual_ip.startswith("127."):
        return manual_ip

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    try:
        fallback = socket.gethostbyname(socket.gethostname())
    except OSError as exc:
        raise QRError(
            "Unable to resolve a LAN IP. Set LOCAL_IP to your machine's WiFi IP address."
        ) from exc
    if fallback.startswith("127."):
        raise QRError(
            "Unable to resolve a LAN IP. Set LOCAL_IP to your machine's WiFi IP address."
        )
    return fallback


def generate_qr(image_path: str) -> str:
    image_file = Path(image_path)
    if not image_file.exists():
        raise QRError(f"Generated image path does not exist: {image_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_url = f"http://{_local_ip()}:8000/static/outputs/{image_file.name}"
    qr_path = OUTPUT_DIR / f"qr_{image_file.stem}.png"

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(image_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img.save(qr_path)
    except OSError as exc:
        raise QRError("Failed to write QR code image.") from exc

    return str(qr_path)
