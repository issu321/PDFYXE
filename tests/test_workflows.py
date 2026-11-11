import io
import time
from pathlib import Path

import pymupdf as fitz

from app.extensions import db
from config import Config


def upload_pdf(client, filename, content):
    return client.post(
        "/pdf/upload",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )


def test_registration_login_and_logout(client, register_and_login):
    response = register_and_login()
    assert b"Dashboard" in response.data
    with client.session_transaction() as session:
        assert "_user_id" in session

    client.post("/auth/logout", follow_redirects=True)
    with client.session_transaction() as session:
        assert "_user_id" not in session
    response = client.post(
        "/auth/login",
        data={"email": "reader@example.com", "password": "securepass123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"My documents" in response.data


def test_upload_preview_and_generate_selected_pages_in_requested_order(
    client, register_and_login, pdf_factory
):
    register_and_login()
    response = upload_pdf(client, "original.pdf", pdf_factory(5))
    assert response.status_code == 201
    document_id = response.json["document_id"]
    assert response.json["pages"] == 5

    preview = client.get(f"/pdf/{document_id}/thumbnail/3")
    assert preview.status_code == 200
    assert preview.mimetype == "image/jpeg"
    assert fitz.open(stream=preview.data, filetype="jpeg").page_count == 1

    request_key = "4bf2daea-3ccb-4f3d-b8bd-9cb99cd72852"
    queued = client.post(
        f"/pdf/{document_id}/generate",
        json={"pages": [5, 2, 4]},
        headers={"Accept": "application/json", "Idempotency-Key": request_key},
    )
    assert queued.status_code == 202
    duplicate = client.post(
        f"/pdf/{document_id}/generate",
        json={"pages": [5, 2, 4]},
        headers={"Accept": "application/json", "Idempotency-Key": request_key},
    )
    assert duplicate.status_code == 202
    assert duplicate.json["job_id"] == queued.json["job_id"]

    for _ in range(100):
        status = client.get(queued.json["status_url"]).json
        if status["status"] != "pending":
            break
        time.sleep(0.02)
    assert status["status"] == "complete"
    assert status["page_count"] == 3
    assert status["selected_pages"] == [5, 2, 4]

    downloaded = client.get(status["download_url"])
    result_pdf = fitz.open(stream=downloaded.data, filetype="pdf")
    assert result_pdf.page_count == 3
    assert [page.get_text().strip() for page in result_pdf] == [
        "PDFCraft test page 5",
        "PDFCraft test page 2",
        "PDFCraft test page 4",
    ]


def test_hundred_page_pdf_and_page_selection(client, register_and_login, pdf_factory):
    register_and_login()
    uploaded = upload_pdf(client, "long-document.pdf", pdf_factory(100))
    assert uploaded.status_code == 201
    assert uploaded.json["pages"] == 100
    workspace = client.get(uploaded.json["workspace_url"])
    assert workspace.status_code == 200
    assert b"Pages 1" in workspace.data
    assert b"Extract selected" in workspace.data
    assert b"Remove selected" in workspace.data
    assert b"operationFeedback" in workspace.data
    assert client.get(f"/pdf/{uploaded.json['document_id']}/thumbnail/100").status_code == 200


def test_rejects_bad_pdf_empty_or_invalid_page_selections(client, register_and_login, pdf_factory):
    register_and_login()
    invalid = upload_pdf(client, "broken.pdf", b"%PDF-not really a document")
    assert invalid.status_code == 422
    uploaded = upload_pdf(client, "valid.pdf", pdf_factory(2))
    document_id = uploaded.json["document_id"]
    assert client.post(f"/pdf/{document_id}/generate", json={"pages": []}).status_code == 400
    assert client.post(f"/pdf/{document_id}/generate", json={"pages": [3]}).status_code == 400
    assert client.post(f"/pdf/{document_id}/generate", json={"pages": [True]}).status_code == 400
    assert client.post(f"/pdf/{document_id}/generate", json=[]).status_code == 400


def test_rejects_encrypted_pdf(client, register_and_login):
    register_and_login()
    document = fitz.open()
    document.new_page()
    encrypted_pdf = document.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner-secret", user_pw="user-secret"
    )
    document.close()
    response = upload_pdf(client, "locked.pdf", encrypted_pdf)
    assert response.status_code == 422
    assert "Password-protected" in response.json["error"]


def test_documents_are_private_to_their_owner(client, register_and_login, pdf_factory):
    register_and_login()
    uploaded = upload_pdf(client, "private.pdf", pdf_factory(1))
    document_id = uploaded.json["document_id"]
    client.post("/auth/logout")
    client.post(
        "/auth/register",
        data={
            "username": "another",
            "email": "another@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
    )
    assert client.get(f"/pdf/{document_id}/workspace").status_code == 404
    assert client.get(f"/pdf/{document_id}/thumbnail/1").status_code == 404
    assert client.post(f"/pdf/{document_id}/generate", json={"pages": [1]}).status_code == 404
    assert client.get(f"/documents/{document_id}/download").status_code == 404


def test_management_pages_render(client, register_and_login):
    register_and_login()
    for path in (
        "/documents/",
        "/documents/generated",
        "/documents/history",
        "/auth/profile",
        "/pdf/merge",
    ):
        response = client.get(path)
        assert response.status_code == 200, path


def test_generated_file_and_records_are_removed_with_source(
    app, client, register_and_login, pdf_factory
):
    register_and_login()
    uploaded = upload_pdf(client, "to-delete.pdf", pdf_factory(2))
    document_id = uploaded.json["document_id"]
    queued = client.post(
        f"/pdf/{document_id}/generate",
        json={"pages": [2]},
        headers={
            "Accept": "application/json",
            "Idempotency-Key": "ca247c02-43d4-47e7-9c27-3e505e27bcdc",
        },
    ).json
    for _ in range(100):
        job = client.get(queued["status_url"]).json
        if job["status"] != "pending":
            break
        time.sleep(0.02)
    assert job["status"] == "complete"
    client.post(f"/documents/{document_id}/delete")
    assert client.get(job["download_url"]).status_code == 404
    with app.app_context():
        from app.models import PDFDocument, ProcessingHistory, ProcessingJob

        assert db.session.get(PDFDocument, document_id) is None
        assert ProcessingHistory.query.count() == 0
        assert ProcessingJob.query.count() == 0


def test_failed_background_extraction_reports_failure(app, client, register_and_login, pdf_factory):
    register_and_login()
    uploaded = upload_pdf(client, "damaged-after-upload.pdf", pdf_factory(1))
    with app.app_context():
        from app.models import PDFDocument

        document = db.session.get(PDFDocument, uploaded.json["document_id"])
        source = Path(app.config["UPLOAD_FOLDER"]) / f"{document.stored_filename}.pdf"
        source.write_bytes(b"not a PDF anymore")
    queued = client.post(
        f"/pdf/{uploaded.json['document_id']}/generate",
        json={"pages": [1]},
        headers={
            "Accept": "application/json",
            "Idempotency-Key": "af083c09-e100-4a46-8119-a53f06977572",
        },
    ).json
    for _ in range(100):
        job = client.get(queued["status_url"]).json
        if job["status"] != "pending":
            break
        time.sleep(0.02)
    assert job["status"] == "failed"
    assert "could not be generated" in job["error"]


def test_remove_pages_preserves_remaining_pages_and_original(
    client, register_and_login, pdf_factory
):
    register_and_login()
    uploaded = upload_pdf(client, "remove-pages.pdf", pdf_factory(4))
    document_id = uploaded.json["document_id"]
    response = client.post(
        f"/pdf/{document_id}/remove",
        json={"pages": [2, 4]},
        headers={
            "Accept": "application/json",
            "Idempotency-Key": "c86507af-7481-430d-8fe1-029890a5c388",
        },
    )
    assert response.status_code == 202
    status_url = response.json["status_url"]
    for _ in range(100):
        job = client.get(status_url).json
        if job["status"] != "pending":
            break
        time.sleep(0.02)
    assert job["status"] == "complete"
    assert job["operation_type"] == "remove"
    output = fitz.open(stream=client.get(job["download_url"]).data, filetype="pdf")
    assert [page.get_text().strip() for page in output] == [
        "PDFCraft test page 1",
        "PDFCraft test page 3",
    ]
    original = client.get(f"/documents/{document_id}/download")
    assert fitz.open(stream=original.data, filetype="pdf").page_count == 4
    assert client.post(f"/pdf/{document_id}/remove", json={"pages": [1, 2, 3, 4]}).status_code == 400
    assert client.post(f"/pdf/{document_id}/remove", json={"pages": []}).status_code == 400


def test_merge_pdfs_preserves_selected_document_order(
    client, register_and_login, pdf_factory
):
    register_and_login()
    first = upload_pdf(client, "first.pdf", pdf_factory(2)).json
    second = upload_pdf(client, "second.pdf", pdf_factory(3)).json
    assert client.get("/pdf/merge").status_code == 200
    queued = client.post(
        "/pdf/merge",
        json={"document_ids": [second["document_id"], first["document_id"]]},
        headers={
            "Accept": "application/json",
            "Idempotency-Key": "7ef7a2dc-a171-4f3e-bdfd-6d3bac06713e",
        },
    )
    assert queued.status_code == 202
    for _ in range(100):
        job = client.get(queued.json["status_url"]).json
        if job["status"] != "pending":
            break
        time.sleep(0.02)
    assert job["status"] == "complete"
    assert job["operation_type"] == "merge"
    assert job["page_count"] == 5
    output = fitz.open(stream=client.get(job["download_url"]).data, filetype="pdf")
    assert [page.get_text().strip() for page in output] == [
        "PDFCraft test page 1",
        "PDFCraft test page 2",
        "PDFCraft test page 3",
        "PDFCraft test page 1",
        "PDFCraft test page 2",
    ]
    assert client.get("/documents/generated").status_code == 200
    client.post(f"/documents/{first['document_id']}/delete")
    assert client.get(job["download_url"]).status_code == 404


def test_merge_validates_count_duplicates_and_ownership(
    client, register_and_login, pdf_factory
):
    register_and_login()
    first = upload_pdf(client, "first.pdf", pdf_factory(1)).json["document_id"]
    assert client.post("/pdf/merge", json={"document_ids": [first]}).status_code == 400
    assert client.post("/pdf/merge", json={"document_ids": [first, first]}).status_code == 400
    client.post("/auth/logout")
    client.post(
        "/auth/register",
        data={
            "username": "another",
            "email": "another@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
    )
    second = upload_pdf(client, "second.pdf", pdf_factory(1)).json["document_id"]
    assert client.post("/pdf/merge", json={"document_ids": [first, second]}).status_code == 404


def test_merge_workspace_has_visible_selection_and_status_controls(
    client, register_and_login, pdf_factory
):
    register_and_login()
    upload_pdf(client, "first.pdf", pdf_factory(1))
    upload_pdf(client, "second.pdf", pdf_factory(1))
    page = client.get("/pdf/merge")
    assert page.status_code == 200
    assert b"Merge selected PDFs" in page.data
    assert b"mergeFeedback" in page.data
    assert b'merge-checkbox' in page.data


def test_upload_size_limit_has_no_default_application_cap(app):
    assert Config.MAX_CONTENT_LENGTH is None
