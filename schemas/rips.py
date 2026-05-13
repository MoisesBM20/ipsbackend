from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from models.rips import RIPSStatus


class RIPSReportCreate(BaseModel):
    period_start: date
    period_end: date
    notes: Optional[str] = None


class RIPSReportResponse(BaseModel):
    id: int
    period_start: date
    period_end: date
    status: RIPSStatus
    total_patients: int
    total_consultations: int
    total_procedures: int
    generated_by: int
    generated_at: datetime
    submitted_at: Optional[datetime]
    notes: Optional[str]

    model_config = {"from_attributes": True}
