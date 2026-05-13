from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from database import Base


class AppointmentStatus(str, Enum):
    SCHEDULED = "agendada"
    CONFIRMED = "confirmada"
    IN_PROGRESS = "en_atencion"
    COMPLETED = "completada"
    CANCELLED = "cancelada"
    NO_SHOW = "no_asistio"
    RESCHEDULED = "reprogramada"


class AppointmentType(str, Enum):
    CONSULTATION = "consulta_medica"
    NURSING = "enfermeria"
    PHYSICAL_THERAPY = "terapia_fisica"
    NUTRITION = "nutricion"
    PSYCHOLOGY = "psicologia"
    POST_SURGICAL = "post_quirurgica"
    SEROTHERAPY = "sueroterapia"
    FOLLOW_UP = "seguimiento"
    EMERGENCY = "urgencia"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    professional_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Fecha y hora
    appointment_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Detalles
    appointment_type = Column(SAEnum(AppointmentType), nullable=False)
    status = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    reason = Column(Text, nullable=True)          # Motivo de consulta
    notes = Column(Text, nullable=True)            # Notas adicionales
    cancellation_reason = Column(Text, nullable=True)

    # Auditoría
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    patient = relationship("Patient", back_populates="appointments")
    professional = relationship("User", foreign_keys=[professional_id], back_populates="appointments_as_professional")
    creator = relationship("User", foreign_keys=[created_by])
