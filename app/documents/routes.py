from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import GeneratedPDF, PDFDocument, ProcessingHistory, ProcessingJob

documents_bp = Blueprint("documents", __name__, url_prefix="/documents")


@documents_bp.get("/")
@login_required
def index():
    documents = (
        PDFDocument.query.filter_by(user_id=current_user.id)
        .order_by(PDFDocument.created_at.desc())
        .all()
    )
    return render_template("documents/index.html", documents=documents)


@documents_bp.get("/generated")
@login_required
def generated():
    items = (
        GeneratedPDF.query.filter_by(user_id=current_user.id)
        .order_by(GeneratedPDF.created_at.desc())
        .all()
    )
    return render_template("documents/generated.html", generated_pdfs=items)


@documents_bp.get("/history")
@login_required
def history():
    items = (
        ProcessingHistory.query.filter_by(user_id=current_user.id)
        .order_by(ProcessingHistory.created_at.desc())
        .all()
    )
    return render_template("documents/history.html", history=items)


@documents_bp.get("/<int:document_id>/download")
@login_required
def download_source(document_id):
    document = PDFDocument.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
    path = Path(current_app.config["UPLOAD_FOLDER"]) / f"{document.stored_filename}.pdf"
    response = send_file(
        path, as_attachment=True, download_name=document.original_filename, mimetype="application/pdf"
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@documents_bp.get("/generated/<int:generated_id>/download")
@login_required
def download_generated(generated_id):
    generated_pdf = GeneratedPDF.query.filter_by(
        id=generated_id, user_id=current_user.id
    ).first_or_404()
    path = Path(current_app.config["GENERATED_FOLDER"]) / f"{generated_pdf.generated_filename}.pdf"
    download_name = (
        "merged-document.pdf"
        if generated_pdf.operation_type == "merge"
        else f"{Path(generated_pdf.source_document.original_filename).stem}-pages.pdf"
    )
    response = send_file(path, as_attachment=True, download_name=download_name, mimetype="application/pdf")
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@documents_bp.post("/<int:document_id>/delete")
@login_required
def delete_document(document_id):
    document = PDFDocument.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
    upload_path = Path(current_app.config["UPLOAD_FOLDER"]) / f"{document.stored_filename}.pdf"
    related_generated = [
        item
        for item in GeneratedPDF.query.filter_by(user_id=current_user.id).all()
        if item.source_document_id == document.id
        or document.id in (item.source_document_ids or [])
    ]
    generated_paths = [
        Path(current_app.config["GENERATED_FOLDER"]) / f"{item.generated_filename}.pdf"
        for item in related_generated
    ]
    for generated_pdf in related_generated:
        db.session.delete(generated_pdf)
    related_jobs = [
        job
        for job in ProcessingJob.query.filter_by(user_id=current_user.id).all()
        if document.id in (job.source_document_ids or [])
    ]
    for job in related_jobs:
        db.session.delete(job)
    db.session.delete(document)
    db.session.commit()
    upload_path.unlink(missing_ok=True)
    for path in generated_paths:
        path.unlink(missing_ok=True)
    flash("The document and its generated PDFs were deleted.", "success")
    return redirect(url_for("documents.index"))


@documents_bp.post("/generated/<int:generated_id>/delete")
@login_required
def delete_generated(generated_id):
    generated_pdf = GeneratedPDF.query.filter_by(
        id=generated_id, user_id=current_user.id
    ).first_or_404()
    path = Path(current_app.config["GENERATED_FOLDER"]) / f"{generated_pdf.generated_filename}.pdf"
    db.session.delete(generated_pdf)
    db.session.commit()
    path.unlink(missing_ok=True)
    flash("The generated PDF was deleted.", "success")
    return redirect(url_for("documents.generated"))
