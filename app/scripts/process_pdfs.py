# scripts/process_pdfs.py
import os
import time
import json
import logging
from pathlib import Path
from tqdm import tqdm
from typing import Optional

# Ensure project root is on path when running as script
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import PayslipRaw, PayslipRecord
from app.extractors.pdf_loader import load_pdf_text
from app.extractors.ocr_fallback import ocr_pdf
from app.extractors.llm_parser import parse_with_llm

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("process_pdfs")

# Controls
PDF_DIR = Path(settings.PDF_FOLDER)
PDF_DIR.mkdir(parents=True, exist_ok=True)
MIN_TEXT_LENGTH_FOR_NO_OCR = 200  # if extracted text shorter -> use OCR fallback
LLM_RETRY_COUNT = 3
LLM_RETRY_BACKOFF = 2  # seconds (exponential backoff base)

# Make sure DB exists / tables created
init_db()

def load_text_with_fallback(path: str) -> str:
    """
    Try to load text with PyPDFLoader first. If the text is short or empty,
    use OCR fallback (pdf2image + pytesseract).
    """
    try:
        text = load_pdf_text(path)
    except Exception as e:
        logger.warning(f"PDF loader failed for {path}: {e}. Falling back to OCR.")
        text = ""

    if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_NO_OCR:
        try:
            ocr_text = ocr_pdf(path)
            if ocr_text and len(ocr_text.strip()) > len(text):
                logger.info(f"OCR produced longer text for {path} (len {len(ocr_text)})")
                return ocr_text
            else:
                logger.info(f"OCR did not improve text length for {path}")
        except Exception as e:
            logger.exception(f"OCR fallback failed for {path}: {e}")
    return text

def llm_parse_with_retries(text: str, retries: int = LLM_RETRY_COUNT) -> dict:
    """
    Call the LLM parser with retries and exponential backoff.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            parsed = parse_with_llm(text)
            # Basic validation: should be a dict
            if isinstance(parsed, dict):
                return parsed
            else:
                raise ValueError("LLM returned non-dict output")
        except Exception as e:
            last_exc = e
            logger.warning(f"LLM parse attempt {attempt}/{retries} failed: {e}")
            sleep_time = LLM_RETRY_BACKOFF ** attempt
            logger.info(f"Sleeping {sleep_time}s before retry...")
            time.sleep(sleep_time)
    # after retries
    raise last_exc

def process_file(path: Path):
    session = SessionLocal()
    try:
        filename = path.name
        # Skip already processed filename (based on PayslipRaw.filename)
        existing = session.query(PayslipRaw).filter_by(filename=filename).first()
        if existing:
            logger.info(f"Skipping {filename}: already processed (id={existing.id}, parsed={existing.parsed})")
            return

        logger.info(f"Processing {filename} ...")
        text = load_text_with_fallback(str(path))

        # Save raw
        raw = PayslipRaw(filename=filename, raw_text=text)
        session.add(raw)
        session.commit()  # so raw.id is available
        logger.debug(f"Saved PayslipRaw id={raw.id}")

        # Parse with LLM (with retries)
        try:
            structured = llm_parse_with_retries(text)
        except Exception as e:
            session.rollback()
            raw.parse_errors = f"LLM parse failed after retries: {repr(e)}"
            session.add(raw)
            session.commit()
            logger.exception(f"LLM parse failed for {filename}; logged error and continuing.")
            return

        # Normalize / safe-extract fields (some fields might be strings)
        def get_number(v):
            if v is None:
                return None
            try:
                if isinstance(v, (int, float)):
                    return v
                # strip commas and currency symbols
                s = str(v).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("INR", "")
                return float(s) if s != "" else None
            except Exception:
                return None

        rec = PayslipRecord(
            payslip_raw_id=raw.id,
            employee_name=structured.get("employee_name"),
            employee_code=structured.get("employee_code"),
            pan=structured.get("pan"),
            pay_date=structured.get("pay_date"),
            month=structured.get("month"),
            gross_salary=get_number(structured.get("gross_salary")),
            basic=get_number(structured.get("basic")),
            hra=get_number(structured.get("hra")),
            special_allowance=get_number(structured.get("special_allowance")),
            tds=get_number(structured.get("tds")),
            pf_employee=get_number(structured.get("pf_employee")),
            pf_employer=get_number(structured.get("pf_employer")),
            net_pay=get_number(structured.get("net_pay")),
            components_json=json.dumps(structured.get("components", {}), ensure_ascii=False)
        )
        session.add(rec)
        raw.parsed = True
        session.add(raw)
        session.commit()
        logger.info(f"Parsed and saved record for {filename} (record id={rec.id})")
    except Exception as e:
        session.rollback()
        logger.exception(f"Unexpected error processing {path}: {e}")
    finally:
        session.close()

def main():
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        logger.info(f"No PDF files found in {PDF_DIR}. Drop your payslips there and re-run.")
        return

    logger.info(f"Found {len(pdfs)} PDF(s) in {PDF_DIR}")
    for p in tqdm(pdfs, desc="Processing PDFs"):
        try:
            process_file(p)
        except Exception as e:
            logger.exception(f"Failed to process {p.name}: {e}")

if __name__ == "__main__":
    main()
