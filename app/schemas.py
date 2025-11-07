from pydantic import BaseModel
from typing import Optional, Dict, Any

class PayslipRecordIn(BaseModel):
    employee_name: Optional[str]
    employee_code: Optional[str]
    pan: Optional[str]
    pay_date: Optional[str]
    month: Optional[str]
    gross_salary: Optional[float]
    basic: Optional[float]
    hra: Optional[float]
    special_allowance: Optional[float]
    tds: Optional[float]
    pf_employee: Optional[float]
    pf_employer: Optional[float]
    net_pay: Optional[float]
    components: Optional[Dict[str, Any]] = {}