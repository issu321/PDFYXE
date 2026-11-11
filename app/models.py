from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    documents = db.relationship(
        "PDFDocument", back_populates="user", cascade="all, delete-orphan"
    )
    generated_pdfs = db.relationship(
        "GeneratedPDF", back_populates="user", cascade="all, delete-orphan"
    )
    history = db.relationship(
        "ProcessingHistory", back_populates="user", cascade="all, delete-orphan"
    )
    processing_jobs = db.relationship(
        "ProcessingJob", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PDFDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(36), unique=True, nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    total_pages = db.Column(db.Integer, nullable=False)
    upload_status = db.Column(db.String(20), nullable=False, default="ready")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user = db.relationship("User", back_populates="documents")
    generated_pdfs = db.relationship(
        "GeneratedPDF", back_populates="source_document", cascade="all, delete-orphan"
    )
    history = db.relationship(
        "ProcessingHistory", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs = db.relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )


class GeneratedPDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    source_document_id = db.Column(
        db.Integer, db.ForeignKey("pdf_document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generated_filename = db.Column(db.String(36), unique=True, nullable=False)
    selected_pages = db.Column(db.JSON, nullable=False)
    operation_type = db.Column(db.String(20), nullable=False, default="extract")
    source_document_ids = db.Column(db.JSON, nullable=False, default=list)
    total_selected_pages = db.Column(db.Integer, nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user = db.relationship("User", back_populates="generated_pdfs")
    source_document = db.relationship("PDFDocument", back_populates="generated_pdfs")


class ProcessingJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("pdf_document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_key = db.Column(db.String(36), nullable=False)
    selected_pages = db.Column(db.JSON, nullable=False)
    operation_type = db.Column(db.String(20), nullable=False, default="extract")
    source_document_ids = db.Column(db.JSON, nullable=False, default=list)
    status = db.Column(db.String(20), nullable=False, default="pending")
    processing_duration = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.String(255), nullable=True)
    generated_pdf_id = db.Column(
        db.Integer, db.ForeignKey("generated_pdf.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    __table_args__ = (
        db.UniqueConstraint("user_id", "request_key", name="uq_processing_job_user_request"),
    )
    user = db.relationship("User", back_populates="processing_jobs")
    document = db.relationship("PDFDocument", back_populates="processing_jobs")


class ProcessingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("pdf_document.id", ondelete="CASCADE"), nullable=True, index=True
    )
    operation_type = db.Column(db.String(30), nullable=False)
    processing_status = db.Column(db.String(20), nullable=False)
    processing_duration = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user = db.relationship("User", back_populates="history")
    document = db.relationship("PDFDocument", back_populates="history")
