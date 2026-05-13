from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from database import Base


class UserRole(str, Enum):
    ADMIN = "admin"                   # Acceso total
    DOCTOR = "doctor"                 # Historias clínicas, citas, disponibilidad propia
    NURSE = "enfermero"               # Ver/actualizar historias, gestionar citas
    RECEPTIONIST = "recepcionista"    # Agendar citas, registrar pacientes
    AUDITOR = "auditor"               # Solo lectura + generación RIPS
    PATIENT = "paciente"              # Solo portal de citas propias


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    document_number = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.RECEPTIONIST)
    specialty = Column(String, nullable=True)   # Ej: "Medicina General", "Enfermería"
    registration_number = Column(String, nullable=True)  # Número de tarjeta profesional
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    availability_slots = relationship("AvailabilitySlot", back_populates="professional")
    appointments_as_professional = relationship(
        "Appointment",
        foreign_keys="[Appointment.professional_id]",
        back_populates="professional",
    )
    clinical_entries = relationship("ClinicalEntry", back_populates="professional")
