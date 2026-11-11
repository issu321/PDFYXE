import pymupdf as fitz
import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path):
    class TestConfig:
        TESTING = True
        SECRET_KEY = "test-secret"
        WTF_CSRF_ENABLED = False
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        MAX_CONTENT_LENGTH = 16 * 1024 * 1024
        UPLOAD_FOLDER = str(tmp_path / "uploads")
        GENERATED_FOLDER = str(tmp_path / "generated")
        THUMBNAIL_CACHE_SECONDS = 60

    application = create_app(TestConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_pdf(page_count):
    document = fitz.open()
    for page_number in range(1, page_count + 1):
        page = document.new_page()
        page.insert_text((72, 72), f"PDFCraft test page {page_number}")
    output = bytearray(document.tobytes())
    document.close()
    return bytes(output)


@pytest.fixture
def pdf_factory():
    return create_pdf


@pytest.fixture
def register_and_login(client):
    def create(email="reader@example.com", username="reader"):
        response = client.post(
            "/auth/register",
            data={
                "username": username,
                "email": email,
                "password": "securepass123",
                "confirm_password": "securepass123",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        return response

    return create
