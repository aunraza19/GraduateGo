import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


class EmailDeliveryError(Exception):
    pass


class EmailConfigError(EmailDeliveryError):
    pass


class EmailSendError(EmailDeliveryError):
    pass


def _smtp_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _smtp_config() -> dict[str, str | int | bool]:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "587").strip())
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    sender = os.getenv("FROM_EMAIL", "").strip() or user
    use_tls = _smtp_bool("SMTP_USE_TLS", True)
    use_ssl = _smtp_bool("SMTP_USE_SSL", False)

    if not host or not user or not password or not sender:
        raise EmailConfigError(
            "SMTP configuration is missing. Set SMTP_HOST, SMTP_USER, SMTP_PASS, and FROM_EMAIL."
        )
    if use_tls and use_ssl:
        raise EmailConfigError("Set only one of SMTP_USE_TLS or SMTP_USE_SSL.")

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender": sender,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
    }


def send_generated_image_email(recipient_email: str, image_path: str) -> None:
    cfg = _smtp_config()
    attachment_path = Path(image_path)
    if not attachment_path.exists():
        raise EmailDeliveryError(f"Image file not found: {image_path}")

    image_bytes = attachment_path.read_bytes()
    if not image_bytes:
        raise EmailDeliveryError("Generated image file is empty.")

    message = EmailMessage()
    message["Subject"] = "Your Graduation Portrait"
    message["From"] = str(cfg["sender"])
    message["To"] = recipient_email
    message.set_content(
        "Your AI-generated graduation portrait is attached.\n\n"
        "Thank you for using the graduation booth."
    )
    message.add_attachment(
        image_bytes,
        maintype="image",
        subtype="jpeg",
        filename=attachment_path.name,
    )

    try:
        if cfg["use_ssl"]:
            with smtplib.SMTP_SSL(str(cfg["host"]), int(cfg["port"]), timeout=30) as server:
                server.login(str(cfg["user"]), str(cfg["password"]))
                server.send_message(message)
            return

        with smtplib.SMTP(str(cfg["host"]), int(cfg["port"]), timeout=30) as server:
            if cfg["use_tls"]:
                server.starttls()
            server.login(str(cfg["user"]), str(cfg["password"]))
            server.send_message(message)
    except smtplib.SMTPException as exc:
        raise EmailSendError(f"SMTP send failed: {exc}") from exc
    except OSError as exc:
        raise EmailSendError(f"SMTP connection failed: {exc}") from exc
