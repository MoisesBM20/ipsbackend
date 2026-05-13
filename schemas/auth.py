from pydantic import BaseModel, EmailStr
from typing import Optional
from models.user import UserRole
from models.patient import DocumentType, Gender, BloodType


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    role: UserRole


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class StaffProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class PatientProfileUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    eps: Optional[str] = None
    regime: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    current_password: Optional[str] = None   # requerido solo si cambia contraseña
    new_password: Optional[str] = None


class PatientRegisterRequest(BaseModel):
    """Registro público de paciente (crea User + Patient vinculados)."""
    email: EmailStr
    password: str
    full_name: str
    document_type: DocumentType
    document_number: str
    birth_date: str        # YYYY-MM-DD
    gender: Gender
    blood_type: BloodType
    phone: str
    address: str
    city: str
    eps: str
    regime: str
