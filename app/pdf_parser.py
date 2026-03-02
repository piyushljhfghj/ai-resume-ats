import fitz  # PyMuPDF

def extract_text_from_pdf(uploaded_file):
    text = ""
    file_bytes = uploaded_file.read()

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()

    return text.strip()