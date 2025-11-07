import os
import json
from app.db import SessionLocal, init_db
from app.models import PayslipRaw, PayslipRecord
from app.extractors.pdf_loader import load_pdf_text
from app.extractors.llm_parser import parse_with_llm
from app.config import settings

init_db()

def process_pdf_file(path: str):
    session = SessionLocal()
    filename = os.path.basename(path)
    existing = session.query(PayslipRaw).filter_by(filename=filename).first()
    if existing:
        session.close()
        return

    text = load_pdf_text(path)
    raw = PayslipRaw(filename=filename, raw_text=text)
    session.add(raw)
    session.commit()

    try:
        structured = parse_with_llm(text)
        rec = PayslipRecord(
            payslip_raw_id=raw.id,
            employee_name=structured.get('employee_name'),
            employee_code=structured.get('employee_code'),
            pan=structured.get('pan'),
            pay_date=structured.get('pay_date'),
            month=structured.get('month'),
            gross_salary=structured.get('gross_salary'),
            basic=structured.get('basic'),
            hra=structured.get('hra'),
            special_allowance=structured.get('special_allowance'),
            tds=structured.get('tds'),
            pf_employee=structured.get('pf_employee'),
            pf_employer=structured.get('pf_employer'),
            net_pay=structured.get('net_pay'),
            components_json=json.dumps(structured.get('components', {}), ensure_ascii=False)
        )
        session.add(rec)
        raw.parsed = True
        session.commit()
    except Exception as e:
        session.rollback()
        raw.parse_errors = str(e)
        session.commit()
    finally:
        session.close()