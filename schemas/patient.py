from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from models.patient import DocumentType, Gender, BloodType


class PatientCreate(BaseModel):
    document_type: DocumentType
    document_number: str
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    blood_type: Optional[BloodType] = BloodType.UNKNOWN

    # Contacto
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = "Cali"
    municipality_code: Optional[str] = "76001"

    # Aseguramiento
    eps: Optional[str] = None
    regime: Optional[str] = None
    affiliate_number: Optional[str] = None

    # Contacto de emergencia
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None

    # Antecedentes
    allergies: Optional[str] = None
    background_notes: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    eps: Optional[str] = None
    regime: Optional[str] = None
    affiliate_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    allergies: Optional[str] = None
    background_notes: Optional[str] = None
    blood_type: Optional[BloodType] = None


class PatientResponse(BaseModel):
    id: int
    document_type: DocumentType
    document_number: str
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    blood_type: Optional[BloodType]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    city: Optional[str]
    eps: Optional[str]
    regime: Optional[str]
    affiliate_number: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    emergency_contact_relationship: Optional[str]
    allergies: Optional[str]
    background_notes: Optional[str]
    created_at: datetime

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    model_config = {"from_attributes": True}


class PatientSummary(BaseModel):
    """Vista resumida para listas y selectores."""
    id: int
    document_type: DocumentType
    document_number: str
    first_name: str
    last_name: str
    birth_date: date
    eps: Optional[str]
    phone: Optional[str]
    user_id: Optional[int] = None
    has_appointment: Optional[bool] = None

    model_config = {"from_attributes": True}
