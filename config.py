import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from the project directory
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

class Config:

    # Gemini API Key
    GEMINI_API_KEY = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_GENAI_API_KEY")
        or ""
    ).strip()

    # Upload Folder
    UPLOAD_FOLDER = "uploads"

    # Maximum Upload Size (10 MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Allowed Image Types
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

    # SMTP Settings for Contact Form
    SMTP_SERVER = os.getenv("SMTP_SERVER", "").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()