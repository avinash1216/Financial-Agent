from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base

class PayslipRaw(Base):
    __tablename__ = "payslips_raw"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), unique=True, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    raw_text = Column(Text)
    parsed = Column(Boolean, default=False)
    parse_errors = Column(Text, nullable=True)
    records = relationship("PayslipRecord", back_populates="raw")

class PayslipRecord(Base):
    __tablename__ = "payslip_records"
    id = Column(Integer, primary_key=True)
    payslip_raw_id = Column(Integer, ForeignKey('payslips_raw.id'))
    employee_name = Column(String(200), nullable=True)
    employee_code = Column(String(100), nullable=True)
    pan = Column(String(20), nullable=True)
    month = Column(String(50), nullable=True)
    pay_date = Column(String(50), nullable=True)
    gross_salary = Column(Numeric(12, 2), nullable=True)
    basic = Column(Numeric(12, 2), nullable=True)
    hra = Column(Numeric(12, 2), nullable=True)
    special_allowance = Column(Numeric(12, 2), nullable=True)
    tds = Column(Numeric(12, 2), nullable=True)
    pf_employee = Column(Numeric(12, 2), nullable=True)
    pf_employer = Column(Numeric(12, 2), nullable=True)
    net_pay = Column(Numeric(12, 2), nullable=True)
    components_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    raw = relationship("PayslipRaw", back_populates="records")