from pypdf import PdfReader, PdfWriter


def extract_pages(source_path, target_path, selected_pages):
    reader = PdfReader(source_path, strict=True)
    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs cannot be processed.")
    if not selected_pages or any(page < 1 or page > len(reader.pages) for page in selected_pages):
        raise ValueError("The page selection is invalid.")
    writer = PdfWriter()
    for page_number in selected_pages:
        writer.add_page(reader.pages[page_number - 1])
    with open(target_path, "wb") as output_file:
        writer.write(output_file)


def merge_pdfs(source_paths, target_path):
    if len(source_paths) < 2:
        raise ValueError("Choose at least two PDFs to merge.")
    writer = PdfWriter()
    total_pages = 0
    for source_path in source_paths:
        reader = PdfReader(source_path, strict=True)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs cannot be merged.")
        total_pages += len(reader.pages)
        writer.append(reader)
    if not total_pages:
        raise ValueError("The selected PDFs do not contain any pages.")
    with open(target_path, "wb") as output_file:
        writer.write(output_file)
