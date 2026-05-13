from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime, timezone as tz
from models.clinical_record import EntryType


def _utc(v):
    """Añade timezone UTC a datetimes naive para serialización correcta."""
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=tz.utc)
    return v


class VitalSigns(BaseModel):
    """Signos vitales estructurados."""
    blood_pressure: Optional[str] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    bmi: Optional[float] = None


class ClinicalEntryCreate(BaseModel):
    clinical_record_id: int
    appointment_id: Optional[int] = None
    entry_type: EntryType

    reason_for_visit: Optional[str] = None
    anamnesis: Optional[str] = None
    physical_exam: Optional[str] = None
    vital_signs: Optional[VitalSigns] = None

    diagnosis_code: Optional[str] = None
    diagnosis_description: Optional[str] = None
    diagnosis_type: Optional[str] = None

    treatment_plan: Optional[str] = None
    prescriptions: Optional[str] = None
    procedures_performed: Optional[str] = None

    referral_destination: Optional[str] = None
    referral_reason: Optional[str] = None

    next_appointment_notes: Optional[str] = None
    additional_notes: Optional[str] = None


class ClinicalEntryResponse(BaseModel):
    id: int
    clinical_record_id: int
    professional_id: int
    professional_name: Optional[str] = None
    appointment_id: Optional[int]
    entry_type: EntryType
    entry_date: datetime

    reason_for_visit: Optional[str]
    anamnesis: Optional[str]
    physical_exam: Optional[str]
    vital_signs: Optional[str]

    diagnosis_code: Optional[str]
    diagnosis_description: Optional[str]
    diagnosis_type: Optional[str]

    treatment_plan: Optional[str]
    prescriptions: Optional[str]
    procedures_performed: Optional[str]

    referral_destination: Optional[str]
    referral_reason: Optional[str]

    next_appointment_notes: Optional[str]
    additional_notes: Optional[str]
    created_at: datetime

    @field_validator('entry_date', 'created_at', mode='before')
    @classmethod
    def make_aware(cls, v):
        return _utc(v)

    model_config = {"from_attributes": True}


class ClinicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    record_number: str
    opened_by: int
    opened_at: datetime
    entries: List[ClinicalEntryResponse] = []

    @field_validator('opened_at', mode='before')
    @classmethod
    def make_aware(cls, v):
        return _utc(v)

    model_config = {"from_attributes": True}
