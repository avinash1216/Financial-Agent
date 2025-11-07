# Simple OCR fallback using pytesseract + Pillow for scanned image PDFs.
from pdf2image import convert_from_path
import pytesseract

def ocr_pdf(path: str) -> str:
    pages = convert_from_path(path)
    texts = []
    for p in pages:
        texts.append(pytesseract.image_to_string(p))
    return '\n\n'.join(texts)