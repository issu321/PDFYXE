from pathlib import Path

from flask import Flask, jsonify, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import event
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy import text

from app.extensions import csrf, db, login_manager


def create_app(config_object="config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["GENERATED_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.documents.routes import documents_bp
    from app.pdf.routes import pdf_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(pdf_bp)

    @app.context_processor
    def inject_user():
        return {"active_user": current_user}

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if app.accept_mimetypes.best == "application/json":
            return jsonify(error="Your session expired. Refresh the page and try again."), 400
        return render_template("error.html", code=400, message=error.description), 400

    @app.errorhandler(413)
    def request_too_large(_error):
        message = "The upload exceeded a request-size limit configured by this app or its hosting platform."
        if app.accept_mimetypes.best == "application/json":
            return jsonify(error=message), 413
        return render_template("error.html", code=413, message=message), 413

    with app.app_context():
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
            event.listen(db.engine, "connect", _enable_sqlite_foreign_keys)
        db.create_all()
        _upgrade_sqlite_columns()

    return app


def _enable_sqlite_foreign_keys(connection, _record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _upgrade_sqlite_columns():
    if not db.engine.dialect.name == "sqlite":
        return
    migrations = {
        "generated_pdf": {
            "operation_type": "VARCHAR(20) NOT NULL DEFAULT 'extract'",
            "source_document_ids": "JSON NOT NULL DEFAULT '[]'",
        },
        "processing_job": {
            "operation_type": "VARCHAR(20) NOT NULL DEFAULT 'extract'",
            "source_document_ids": "JSON NOT NULL DEFAULT '[]'",
        },
    }
    inspector = sqlalchemy_inspect(db.engine)
    for table_name, columns in migrations.items():
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, definition in columns.items():
            if column_name not in existing:
                db.session.execute(
                    text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}')
                )
    db.session.commit()
