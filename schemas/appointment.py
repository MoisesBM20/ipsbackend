from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, time, datetime, timezone as tz
from models.appointment import AppointmentStatus, AppointmentType


class AppointmentCreate(BaseModel):
    patient_id: int
    professional_id: int
    appointment_date: date
    start_time: time
    appointment_type: AppointmentType
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    appointment_date: Optional[date] = None
    start_time: Optional[time] = None
    professional_id: Optional[int] = None


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None        # Nombre completo del paciente
    patient_document: Optional[str] = None    # Documento del paciente
    professional_id: int
    professional_name: Optional[str] = None   # Nombre del profesional
    appointment_date: date
    start_time: time
    end_time: time
    appointment_type: AppointmentType
    status: AppointmentStatus
    reason: Optional[str]
    notes: Optional[str]
    cancellation_reason: Optional[str]
    created_at: datetime

    @field_validator('created_at', mode='before')
    @classmethod
    def make_aware(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=tz.utc)
        return v

    model_config = {"from_attributes": True}


class CalendarDay(BaseModel):
    """Vista de calendario para un día con sus citas."""
    date: date
    appointments: list[AppointmentResponse]
    total: int
