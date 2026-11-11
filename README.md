# PDFCraft

PDFCraft is a private PDF workspace built with Flask, SQLAlchemy, Flask-Login, PyMuPDF, and pypdf. It uploads and validates PDFs, renders page previews on demand, extracts or removes selected pages, merges PDFs in a chosen order, and creates new PDFs from original page objects.

## Run locally

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python run.py
```

Set `SECRET_KEY` to a long random value before using the app beyond local development. The example key in the configuration is for local startup only. Set `COOKIE_SECURE=1` when serving over HTTPS. There is no built-in maximum page count or application-level upload-size cap by default. To impose an optional request limit, set `MAX_UPLOAD_BYTES` to a byte count. Real maximum file sizes still depend on available disk, memory, request timeouts, and any reverse proxy or hosting limits. `PDF_UPLOAD_FOLDER` and `PDF_GENERATED_FOLDER` should point to private, non-public storage locations in production.

Open [http://127.0.0.1:5000](http://127.0.0.1:5000), create an account, upload PDFs, and extract or remove pages in the editor. Use **Merge PDFs** to combine two or more library documents in a drag-and-drop order. `app.sh` and `app.bat` are convenience launchers.

## Features

- User registration, login/logout, password hashing, CSRF protection, secure sessions, and password change.
- Private document library, generated PDF downloads, processing history, and ownership checks on document, preview, output, and deletion routes.
- PDF signature and parser validation, encrypted-PDF rejection, UUID storage names, optional configurable request-size limit, and server-side page selection validation.
- On-demand low-resolution thumbnails, paginated in batches of 48, with browser lazy-loading.
- Individual, all, odd, even, and custom-range selection, with a paginated reorder strip for large selections.
- Extraction in a bounded background thread pool. Status is persisted and polled by the editor; request idempotency keys prevent duplicate queued jobs.
- Page extraction uses pypdf page objects, not raster images, preserving the selected source page content and order.
- Page removal creates a new PDF containing every unmarked page in its original order; source files are never modified.
- PDF merging combines two or more owned source PDFs in the user-selected order and retains the original PDF pages.

## Storage and database

SQLite is used by default at `instance/pdfcraft.db`. Uploaded and generated files are stored outside Flask's static directory. The database is initialized automatically on application startup and the additive schema changes are applied to existing SQLite databases. Back up the database and files together.

The in-process job pool is bounded to two simultaneous PDF tasks per application process. For multi-process or horizontally scaled deployment, use a shared durable task queue and shared private storage, and secure the deployment behind HTTPS with an appropriately configured production WSGI server. Very large PDFs can still be constrained by available storage, memory, processing timeouts, or deployment-level request limits.

## Tests

Run the included focused workflow suite with:

```sh
python -m pytest
```

The tests cover registration/login/logout, a 100-page upload, previews, asynchronous extraction, page removal, ordered merging, output content, invalid selections, corrupted PDFs, and cross-user access denial.
