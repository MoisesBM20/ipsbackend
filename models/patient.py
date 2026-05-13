from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from database import Base


class DocumentType(str, Enum):
    CC = "CC"       # Cédula de ciudadanía
    TI = "TI"       # Tarjeta de identidad
    CE = "CE"       # Cédula de extranjería
    PA = "PA"       # Pasaporte
    RC = "RC"       # Registro civil
    MS = "MS"       # Menor sin identificación
    AS = "AS"       # Adulto sin identificación
    NIT = "NIT"     # NIT (para empresas)


class Gender(str, Enum):
    M = "M"         # Masculino
    F = "F"         # Femenino
    I = "I"         # Indeterminado/Intersexual


class BloodType(str, Enum):
    A_POS = "A_POS"
    A_NEG = "A_NEG"
    B_POS = "B_POS"
    B_NEG = "B_NEG"
    AB_POS = "AB_POS"
    AB_NEG = "AB_NEG"
    O_POS = "O_POS"
    O_NEG = "O_NEG"
    UNKNOWN = "UNKNOWN"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(SAEnum(DocumentType), nullable=False)
    document_number = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    gender = Column(SAEnum(Gender), nullable=False)
    blood_type = Column(SAEnum(BloodType), nullable=True)

    # Contacto
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True, default="Cali")
    municipality_code = Column(String, nullable=True, default="76001")  # Para RIPS

    # Aseguramiento
    eps = Column(String, nullable=True)           # EPS o aseguradora
    regime = Column(String, nullable=True)        # Contributivo, Subsidiado, Vinculado
    affiliate_number = Column(String, nullable=True)

    # Contacto de emergencia
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    emergency_contact_relationship = Column(String, nullable=True)

    # Antecedentes médicos (texto libre inicial)
    allergies = Column(String, nullable=True)
    background_notes = Column(String, nullable=True)

    # Cuenta de usuario vinculada (paciente auto-registrado)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    user = relationship("User", foreign_keys=[user_id])
    appointments = relationship("Appointment", back_populates="patient")
    clinical_record = relationship("ClinicalRecord", back_populates="patient", uselist=False)
