import fitz  # PyMuPDF

def extract_text_from_pdf(uploaded_file):
    """
    Extract text from PDF.
    If normal text layer is empty (scanned PDF),
    automatically fallback to OCR using PyMuPDF built-in OCR.
    """

    text = ""

    # Read file bytes once
    file_bytes = uploaded_file.read()

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:

        for page in doc:
            page_text = page.get_text()

            # If page has readable text
            if page_text and page_text.strip():
                text += page_text

            else:
                # Fallback to OCR (for scanned resumes)
                try:
                    ocr_text = page.get_text("ocr")
                    text += ocr_text
                except Exception:
                    pass  # Skip if OCR fails

    return text.strip()