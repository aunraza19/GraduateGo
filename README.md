# IU-AICIS AI Graduation Booth

AI Graduation Booth is an interactive Society Day activity built for **Iqra University** by **IU-AICIS**  
(Iqra University Artificial Intelligence, Advanced Computing, and Information Security Society).

This project lets students stand in front of a camera, capture their photo with a countdown, and receive an AI-generated portrait of themselves in an Iqra University graduation gown and cap.

Prepared and led by the society AI team.

---

## Event Context

This booth was designed for **Society Day at Iqra University** as an engaging, future-focused student experience:

- Students visit the booth
- A live camera captures their photo (`3-2-1` countdown)
- AI transforms the image into a graduation-style portrait
- The image can be delivered by email directly from the booth app

---

## What This Project Does

- Runs a FastAPI backend for image generation workflow
- Uses **OpenAI GPT Image model** (`gpt-image-1.5`) for image edits/generation
- Uses local reference images to guide output style
- Saves uploads and generated outputs locally
- Generates QR image (optional/local-network use)
- Sends generated image via Gmail SMTP
- Provides a camera-first web interface with fallback file upload

---

## Core Features

- Camera capture with live preview
- `3-2-1` countdown before photo capture
- Automatic submit of captured image to backend
- AI-generated graduation portrait output
- Email delivery button + optional auto-send when email is entered
- Robust JSON error handling for upload/API/config/file/email issues
- Local static hosting of generated files

---

## Tech Stack

- Python
- FastAPI
- OpenAI Images API (GPT Image)
- `requests`
- `qrcode`
- Gmail SMTP (`smtplib`)
- Simple HTML/CSS/JS frontend

---

## Project Structure

```text
GraduateGo/
├── backend/
│   ├── main.py
│   ├── services/
│   │   ├── openai_image.py
│   │   ├── storage.py
│   │   ├── qr.py
│   │   └── email_delivery.py
│   ├── static/
│   │   ├── index.html
│   │   ├── inputs/
│   │   └── outputs/
│   └── utils/
│       ├── prompt.py
│       └── env_loader.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.11+ (project currently tested with local venv setup)
- OpenAI API key with image generation access
- Gmail account with 2FA and App Password (for email sending)

---

## Setup

### 1) Clone and install dependencies

```bash
git clone <your-repo-url>
cd GraduateGo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Create environment file

```bash
cp .env.example .env
```

Fill required values in `.env`.

---

## Environment Variables

### OpenAI

- `OPENAI_API_KEY` (required)
- `OPENAI_IMAGE_MODEL` (default: `gpt-image-1.5`)
- `OPENAI_REFERENCE_IMAGES` (optional, comma-separated paths)
- `OPENAI_IMAGE_SIZE` (optional)
- `OPENAI_IMAGE_QUALITY` (optional)
- `OPENAI_IMAGE_FORMAT` (optional)

### Local networking / QR

- `LOCAL_IP` (optional but recommended for LAN QR usage)

### Gmail SMTP

- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_USER=<your-gmail>`
- `SMTP_PASS=<gmail-app-password>`
- `FROM_EMAIL=<your-gmail>`
- `SMTP_USE_TLS=true`

---

## Reference Images

Place reference images in:

`backend/static/inputs/`

Examples:

- `backend/static/inputs/reference1.jpg`
- `backend/static/inputs/reference2.jpeg`
- `backend/static/inputs/reference3.jpg`

You may also explicitly set:

```dotenv
OPENAI_REFERENCE_IMAGES=static/inputs/reference1.jpg,static/inputs/reference2.jpg
```

---

## Run the App

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open in browser:

- Local machine: `http://localhost:8000`

---

## Booth Usage Flow

1. Open the web app on booth laptop
2. Click **Start Camera**
3. Student stands in front of camera
4. Click **Click Photo**
5. Countdown runs (`3-2-1`)
6. Portrait is generated
7. Enter student email and send image

Fallback:

- If camera permission fails, use file upload input on the page

---

## API Endpoints

### `POST /generate`

- Input: `multipart/form-data` with field `file`
- Output:

```json
{
  "image_url": "/static/outputs/<file>.jpg",
  "qr_url": "/static/outputs/qr_<file>.png"
}
```

### `POST /deliver-email`

- Input:

```json
{
  "email": "student@example.com",
  "image_url": "/static/outputs/<file>.jpg"
}
```

- Output:

```json
{
  "message": "Image sent successfully."
}
```

---

## Gmail Setup Notes

For Gmail SMTP to work:

1. Enable Google account 2-Step Verification
2. Generate a Gmail App Password
3. Use App Password in `SMTP_PASS`

Do not use your normal Gmail account password in `SMTP_PASS`.

---

## Troubleshooting

### `OpenAI configuration error: OPENAI_API_KEY is not set`

- Check `.env` location:
  - `GraduateGo/.env` or `GraduateGo/backend/.env`
- Ensure exact format:

```dotenv
OPENAI_API_KEY=sk-...
```

- Restart server after changes

### `OpenAI API failure (401 invalid_api_key)`

- API key is present but incorrect/expired

### `OpenAI API failure (429 quota exceeded)`

- Your OpenAI project has hit rate/usage limits
- Wait and retry, or use a key/project with available quota

### Email sending fails

- Confirm `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`
- Ensure Gmail App Password is used
- Check internet access and firewall rules

### Camera not working in browser

- Allow camera permission in browser settings
- Use fallback file upload if camera is blocked

---

## Privacy & Operations Notes

- Captured and generated images are stored locally in:
  - `backend/static/inputs/`
  - `backend/static/outputs/`
- For public events, define a retention policy (e.g., delete old files after event/day)
- Avoid collecting unnecessary personal information

---

## Credits

Built for **Iqra University Society Day** under **IU-AICIS**  
Project lead context: AI team leadership from the society side.

If you are deploying this booth with new volunteers, share this README with them before event day for quick onboarding.
