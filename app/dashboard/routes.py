from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models import GeneratedPDF, PDFDocument, ProcessingHistory

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
@login_required
def index():
    document_count = PDFDocument.query.filter_by(user_id=current_user.id).count()
    generated_count = GeneratedPDF.query.filter_by(user_id=current_user.id).count()
    pages_processed = db.session.query(
        func.coalesce(func.sum(GeneratedPDF.total_selected_pages), 0)
    ).filter_by(user_id=current_user.id).scalar()
    recent_documents = (
        PDFDocument.query.filter_by(user_id=current_user.id)
        .order_by(PDFDocument.created_at.desc())
        .limit(5)
        .all()
    )
    recent_generated = (
        GeneratedPDF.query.filter_by(user_id=current_user.id)
        .order_by(GeneratedPDF.created_at.desc())
        .limit(5)
        .all()
    )
    recent_history = (
        ProcessingHistory.query.filter_by(user_id=current_user.id)
        .order_by(ProcessingHistory.created_at.desc())
        .limit(6)
        .all()
    )

    doc_storage = (
        db.session.query(func.coalesce(func.sum(PDFDocument.file_size), 0))
        .filter_by(user_id=current_user.id)
        .scalar()
    )
    gen_storage = (
        db.session.query(func.coalesce(func.sum(GeneratedPDF.file_size), 0))
        .filter_by(user_id=current_user.id)
        .scalar()
    )
    storage_bytes = doc_storage + gen_storage

    total_ops = ProcessingHistory.query.filter_by(user_id=current_user.id).count()
    completed_ops = ProcessingHistory.query.filter_by(
        user_id=current_user.id, processing_status="complete"
    ).count()
    success_rate = round((completed_ops / total_ops) * 100) if total_ops > 0 else 100

    extract_count = ProcessingHistory.query.filter_by(
        user_id=current_user.id, operation_type="extract"
    ).count()
    merge_count = ProcessingHistory.query.filter_by(
        user_id=current_user.id, operation_type="merge"
    ).count()
    remove_count = ProcessingHistory.query.filter_by(
        user_id=current_user.id, operation_type="remove"
    ).count()
    upload_count = ProcessingHistory.query.filter_by(
        user_id=current_user.id, operation_type="upload"
    ).count()

    today = datetime.utcnow().date()
    daily_stats = []
    max_metric = 1
    for day_idx in range(6, -1, -1):
        target_date = today - timedelta(days=day_idx)
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        day_pages = (
            db.session.query(func.coalesce(func.sum(GeneratedPDF.total_selected_pages), 0))
            .filter(
                GeneratedPDF.user_id == current_user.id,
                GeneratedPDF.created_at >= start_dt,
                GeneratedPDF.created_at <= end_dt,
            )
            .scalar()
        )
        day_ops = (
            ProcessingHistory.query.filter(
                ProcessingHistory.user_id == current_user.id,
                ProcessingHistory.created_at >= start_dt,
                ProcessingHistory.created_at <= end_dt,
            ).count()
        )
        p_count = int(day_pages)
        o_count = int(day_ops)
        if p_count > max_metric:
            max_metric = p_count
        if o_count * 5 > max_metric:
            max_metric = o_count * 5
        daily_stats.append({
            "label": target_date.strftime("%a"),
            "full_date": target_date.strftime("%b %d"),
            "pages": p_count,
            "ops": o_count,
        })

    # Precalculate safe, strictly bounded SVG bar coordinates (100% leak proof)
    for day in daily_stats:
        ratio = day["pages"] / max_metric if max_metric > 0 else 0
        h = round(ratio * 120)
        if day["pages"] > 0 and h < 8:
            h = 8
        day["bar_h"] = min(120, max(0, h))
        day["bar_y"] = 180 - day["bar_h"]
        op_h = round((day["ops"] * 5 / max_metric) * 100) if max_metric > 0 else 0
        day["op_y"] = max(30, min(180, 180 - op_h))

    return render_template(
        "dashboard/index.html",
        document_count=document_count,
        generated_count=generated_count,
        pages_processed=pages_processed,
        recent_documents=recent_documents,
        recent_generated=recent_generated,
        recent_history=recent_history,
        storage_bytes=storage_bytes,
        success_rate=success_rate,
        extract_count=extract_count,
        merge_count=merge_count,
        remove_count=remove_count,
        upload_count=upload_count,
        daily_stats=daily_stats,
    )
