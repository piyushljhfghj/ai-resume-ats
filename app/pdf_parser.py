import fitz
import pytesseract
from PIL import Image
import io

def extract_text_from_pdf(uploaded_file):

    text = ""  

    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()

        # If text empty → apply OCR
        if len(text.strip()) < 50:

            for page in doc:
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))

                ocr_text = pytesseract.image_to_string(image)
                text += ocr_text

    return text.strip()