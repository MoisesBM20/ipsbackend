from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    document_number: str
    phone: Optional[str] = None
    role: UserRole = UserRole.RECEPTIONIST
    specialty: Optional[str] = None
    registration_number: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    specialty: Optional[str] = None
    registration_number: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    document_number: str
    phone: Optional[str]
    role: UserRole
    specialty: Optional[str]
    registration_number: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    """Vista resumida para listas y selectores."""
    id: int
    full_name: str
    role: UserRole
    specialty: Optional[str]

    model_config = {"from_attributes": True}
