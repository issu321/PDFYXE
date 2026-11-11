import os
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf as fitz
from flask import Blueprint, abort, current_app, jsonify, make_response, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import GeneratedPDF, PDFDocument, ProcessingHistory, ProcessingJob
from app.pdf.processor import extract_pages, merge_pdfs
from app.pdf.validators import PDFValidationError, validate_pdf_upload

pdf_bp = Blueprint("pdf", __name__, url_prefix="/pdf")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pdfcraft-extract")


def owned_document(document_id):
    document = PDFDocument.query.filter_by(id=document_id, user_id=current_user.id).first()
    if document is None:
        abort(404)
    return document


def stored_path(folder_key, filename):
    return Path(current_app.config[folder_key]) / filename


@pdf_bp.post("/upload")
@login_required
def upload():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="Choose a PDF to upload."), 400
    storage_name = f"{uuid.uuid4()}.pdf"
    target_path = stored_path("UPLOAD_FOLDER", storage_name)
    try:
        original_filename, page_count = validate_pdf_upload(uploaded_file, target_path)
        file_size = target_path.stat().st_size
        document = PDFDocument(
            user_id=current_user.id,
            original_filename=original_filename,
            stored_filename=storage_name[:-4],
            file_size=file_size,
            total_pages=page_count,
            upload_status="ready",
        )
        db.session.add(document)
        db.session.flush()
        db.session.add(
            ProcessingHistory(
                user_id=current_user.id,
                document_id=document.id,
                operation_type="upload",
                processing_status="complete",
                processing_duration=0,
            )
        )
        db.session.commit()
        return jsonify(
            document_id=document.id,
            filename=document.original_filename,
            pages=document.total_pages,
            size=document.file_size,
            workspace_url=url_for("pdf.workspace", document_id=document.id),
        ), 201
    except PDFValidationError as error:
        target_path.unlink(missing_ok=True)
        return jsonify(error=str(error)), 422
    except Exception:
        db.session.rollback()
        target_path.unlink(missing_ok=True)
        current_app.logger.exception("PDF upload processing failed")
        return jsonify(error="The PDF could not be processed. Please try another file."), 500


@pdf_bp.get("/<int:document_id>/workspace")
@login_required
def workspace(document_id):
    document = owned_document(document_id)
    return render_template("pdf/workspace.html", document=document)


@pdf_bp.get("/merge")
@login_required
def merge_workspace():
    documents = (
        PDFDocument.query.filter_by(user_id=current_user.id)
        .order_by(PDFDocument.created_at.desc())
        .all()
    )
    return render_template("pdf/merge.html", documents=documents)


@pdf_bp.get("/<int:document_id>/thumbnail/<int:page_number>")
@login_required
def thumbnail(document_id, page_number):
    document = owned_document(document_id)
    if page_number < 1 or page_number > document.total_pages:
        abort(404)
    source = stored_path("UPLOAD_FOLDER", f"{document.stored_filename}.pdf")
    try:
        with fitz.open(source) as pdf:
            page = pdf.load_page(page_number - 1)
            rect = page.rect
            scale = min(0.55, 480 / max(rect.width, rect.height))
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = pixmap.tobytes("jpeg", jpg_quality=72)
    except (fitz.FileDataError, RuntimeError, OSError):
        current_app.logger.exception("Could not render a PDF thumbnail")
        abort(422)
    response = make_response(image)
    response.headers["Content-Type"] = "image/jpeg"
    response.headers["Cache-Control"] = f"private, max-age={current_app.config['THUMBNAIL_CACHE_SECONDS']}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@pdf_bp.post("/<int:document_id>/generate")
@login_required
def generate(document_id):
    document = owned_document(document_id)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="The page selection must be a JSON object."), 400
    pages = payload.get("pages")
    if (
        not isinstance(pages, list)
        or not pages
        or any(type(page) is not int for page in pages)
        or len(set(pages)) != len(pages)
        or any(page < 1 or page > document.total_pages for page in pages)
    ):
        return jsonify(error="Select one or more valid pages in the order you want them."), 400

    return enqueue_pdf_job(
        document=document,
        pages=pages,
        operation_type="extract",
        source_document_ids=[document.id],
    )


@pdf_bp.post("/<int:document_id>/remove")
@login_required
def remove_pages(document_id):
    document = owned_document(document_id)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="The page selection must be a JSON object."), 400
    excluded = payload.get("pages")
    if (
        not isinstance(excluded, list)
        or not excluded
        or any(type(page) is not int for page in excluded)
        or len(set(excluded)) != len(excluded)
        or any(page < 1 or page > document.total_pages for page in excluded)
    ):
        return jsonify(error="Select one or more valid pages to remove."), 400
    removed = set(excluded)
    remaining_pages = [
        page_number
        for page_number in range(1, document.total_pages + 1)
        if page_number not in removed
    ]
    if not remaining_pages:
        return jsonify(error="A PDF must contain at least one page. Leave one page unselected."), 400
    return enqueue_pdf_job(
        document=document,
        pages=remaining_pages,
        operation_type="remove",
        source_document_ids=[document.id],
    )


@pdf_bp.post("/merge")
@login_required
def queue_merge():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Choose PDFs to merge."), 400
    document_ids = payload.get("document_ids")
    if (
        not isinstance(document_ids, list)
        or len(document_ids) < 2
        or any(type(document_id) is not int or document_id < 1 for document_id in document_ids)
        or len(set(document_ids)) != len(document_ids)
    ):
        return jsonify(error="Choose at least two different PDFs to merge."), 400
    documents = (
        PDFDocument.query.filter(
            PDFDocument.user_id == current_user.id,
            PDFDocument.id.in_(document_ids),
        ).all()
    )
    documents_by_id = {document.id: document for document in documents}
    if len(documents_by_id) != len(document_ids):
        abort(404)
    primary = documents_by_id[document_ids[0]]
    return enqueue_pdf_job(
        document=primary,
        pages=[],
        operation_type="merge",
        source_document_ids=document_ids,
    )


def enqueue_pdf_job(document, pages, operation_type, source_document_ids):
    request_key = request.headers.get("Idempotency-Key", "")
    try:
        request_key = str(uuid.UUID(request_key))
    except (ValueError, AttributeError):
        return jsonify(error="A valid request key is required. Refresh and try again."), 400

    existing_job = ProcessingJob.query.filter_by(
        user_id=current_user.id, request_key=request_key
    ).first()
    if existing_job:
        if (
            existing_job.document_id != document.id
            or existing_job.selected_pages != pages
            or existing_job.operation_type != operation_type
            or existing_job.source_document_ids != source_document_ids
        ):
            return jsonify(error="This request key was already used for a different page selection."), 409
        return jsonify(job_id=existing_job.id, status_url=url_for("pdf.job_status", job_id=existing_job.id)), 202

    job = ProcessingJob(
        user_id=current_user.id,
        document_id=document.id,
        request_key=request_key,
        selected_pages=pages,
        operation_type=operation_type,
        source_document_ids=source_document_ids,
        status="pending",
    )
    db.session.add(job)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_job = ProcessingJob.query.filter_by(
            user_id=current_user.id, request_key=request_key
        ).first()
        if existing_job is None:
            current_app.logger.exception("Could not save an extraction job")
            return jsonify(error="The PDF job could not be queued. Please try again."), 500
        if (
            existing_job.document_id != document.id
            or existing_job.selected_pages != pages
            or existing_job.operation_type != operation_type
            or existing_job.source_document_ids != source_document_ids
        ):
            return jsonify(error="This request key was already used for a different page selection."), 409
        return jsonify(job_id=existing_job.id, status_url=url_for("pdf.job_status", job_id=existing_job.id)), 202
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not save an extraction job")
        return jsonify(error="The PDF job could not be queued. Please try again."), 500

    application = current_app._get_current_object()
    _executor.submit(run_pdf_job, application, job.id)
    return jsonify(job_id=job.id, status_url=url_for("pdf.job_status", job_id=job.id)), 202


def run_pdf_job(application, job_id):
    with application.app_context():
        job = db.session.get(ProcessingJob, job_id)
        if job is None or job.status != "pending":
            return
        document = db.session.get(PDFDocument, job.document_id)
        if document is None:
            return
        start = time.monotonic()
        generated_name = str(uuid.uuid4())
        output_folder = Path(application.config["GENERATED_FOLDER"])
        output_path = output_folder / f"{generated_name}.pdf"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=output_folder, prefix=".pdfcraft-", suffix=".tmp", delete=False
            ) as temp:
                temp_path = Path(temp.name)
            source_documents = (
                PDFDocument.query.filter(
                    PDFDocument.user_id == job.user_id,
                    PDFDocument.id.in_(job.source_document_ids),
                ).all()
            )
            documents_by_id = {source.id: source for source in source_documents}
            if len(documents_by_id) != len(job.source_document_ids):
                raise ValueError("A source PDF is no longer available.")
            if job.operation_type == "merge":
                source_paths = [
                    stored_path(
                        "UPLOAD_FOLDER",
                        f"{documents_by_id[source_id].stored_filename}.pdf",
                    )
                    for source_id in job.source_document_ids
                ]
                merge_pdfs(source_paths, temp_path)
                total_pages = sum(
                    documents_by_id[source_id].total_pages for source_id in job.source_document_ids
                )
            else:
                source_path = stored_path("UPLOAD_FOLDER", f"{document.stored_filename}.pdf")
                extract_pages(source_path, temp_path, job.selected_pages)
                total_pages = len(job.selected_pages)
            os.replace(temp_path, output_path)
            duration = round(time.monotonic() - start, 3)
            generated = GeneratedPDF(
                user_id=job.user_id,
                source_document_id=document.id,
                generated_filename=generated_name,
                selected_pages=job.selected_pages,
                operation_type=job.operation_type,
                source_document_ids=job.source_document_ids,
                total_selected_pages=total_pages,
                file_size=output_path.stat().st_size,
            )
            db.session.add(generated)
            db.session.flush()
            job.status = "complete"
            job.processing_duration = duration
            job.generated_pdf_id = generated.id
            db.session.add(
                ProcessingHistory(
                    user_id=job.user_id,
                    document_id=document.id,
                    operation_type=job.operation_type,
                    processing_status="complete",
                    processing_duration=duration,
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            output_path.unlink(missing_ok=True)
            current_app.logger.exception("PDF extraction job failed")
            failed_job = db.session.get(ProcessingJob, job_id)
            if failed_job is not None:
                failed_job.status = "failed"
                failed_job.processing_duration = round(time.monotonic() - start, 3)
                failed_job.error_message = "The PDF could not be generated. Try a different page selection."
                db.session.add(
                    ProcessingHistory(
                        user_id=failed_job.user_id,
                        document_id=failed_job.document_id,
                        operation_type=failed_job.operation_type,
                        processing_status="failed",
                        processing_duration=failed_job.processing_duration,
                    )
                )
                db.session.commit()
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)


@pdf_bp.get("/jobs/<int:job_id>")
@login_required
def job_status(job_id):
    job = ProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    result = {"job_id": job.id, "status": job.status}
    if job.status == "failed":
        result["error"] = job.error_message or "The PDF could not be generated."
    if job.status == "complete" and job.generated_pdf_id:
        generated = db.session.get(GeneratedPDF, job.generated_pdf_id)
        document = db.session.get(PDFDocument, job.document_id)
        if generated is None or document is None:
            return jsonify(error="The completed PDF is no longer available."), 410
        result.update(
            generated_id=generated.id,
            operation_type=generated.operation_type,
            filename=(
                "merged-document.pdf"
                if generated.operation_type == "merge"
                else f"{Path(document.original_filename).stem}-pages.pdf"
            ),
            original_filename=(
                f"{len(generated.source_document_ids)} PDFs"
                if generated.operation_type == "merge"
                else document.original_filename
            ),
            original_pages=sum(
                source.total_pages
                for source in PDFDocument.query.filter(
                    PDFDocument.user_id == current_user.id,
                    PDFDocument.id.in_(generated.source_document_ids),
                ).all()
            ),
            selected_pages=generated.selected_pages,
            page_count=generated.total_selected_pages,
            duration=job.processing_duration,
            download_url=url_for("documents.download_generated", generated_id=generated.id),
        )
    return jsonify(result)
