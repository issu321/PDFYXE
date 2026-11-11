from pathlib import Path

import pymupdf as fitz
from werkzeug.utils import secure_filename


class PDFValidationError(ValueError):
    pass


def validate_pdf_upload(file_storage, target_path):
    original_filename = secure_filename(file_storage.filename or "")
    if not original_filename or Path(original_filename).suffix.lower() != ".pdf":
        raise PDFValidationError("Choose a file with a .pdf extension.")
    header = file_storage.stream.read(5)
    file_storage.stream.seek(0)
    if header != b"%PDF-":
        raise PDFValidationError("This file does not have a valid PDF signature.")
    file_storage.save(target_path)
    try:
        with fitz.open(target_path) as document:
            if document.is_encrypted:
                raise PDFValidationError("Password-protected PDFs are not supported. Remove the password and try again.")
            if document.page_count < 1:
                raise PDFValidationError("This PDF does not contain any pages.")
            return original_filename, document.page_count
    except PDFValidationError:
        raise
    except (fitz.FileDataError, RuntimeError, ValueError) as error:
        raise PDFValidationError("This PDF is damaged or could not be opened.") from error
