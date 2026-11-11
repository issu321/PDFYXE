import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'pdfcraft.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    _upload_limit = os.environ.get("MAX_UPLOAD_BYTES")
    MAX_CONTENT_LENGTH = (
        int(_upload_limit) if _upload_limit and _upload_limit.lower() != "none" else None
    )
    UPLOAD_FOLDER = os.environ.get("PDF_UPLOAD_FOLDER", str(BASE_DIR / "storage" / "uploads"))
    GENERATED_FOLDER = os.environ.get(
        "PDF_GENERATED_FOLDER", str(BASE_DIR / "storage" / "generated")
    )
    THUMBNAIL_CACHE_SECONDS = 300
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    WTF_CSRF_TIME_LIMIT = 3600
