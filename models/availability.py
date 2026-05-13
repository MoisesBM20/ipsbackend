from sqlalchemy import Column, Integer, String, Boolean, Time, ForeignKey, Enum as SAEnum, Date
from sqlalchemy.orm import relationship
from enum import Enum
from database import Base


class DayOfWeek(str, Enum):
    MONDAY = "lunes"
    TUESDAY = "martes"
    WEDNESDAY = "miercoles"
    THURSDAY = "jueves"
    FRIDAY = "viernes"
    SATURDAY = "sabado"
    SUNDAY = "domingo"


class AvailabilitySlot(Base):
    """
    Define la disponibilidad semanal de un profesional.
    Ej: Doctor García disponible los lunes de 8:00 a 12:00, slots de 30 min.
    """
    __tablename__ = "availability_slots"

    id = Column(Integer, primary_key=True, index=True)
    professional_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(SAEnum(DayOfWeek), nullable=False)
    start_time = Column(Time, nullable=False)   # Ej: 08:00
    end_time = Column(Time, nullable=False)     # Ej: 12:00
    slot_duration_minutes = Column(Integer, default=30)  # Duración de cada cita
    service_type = Column(String, nullable=True)  # Tipo de servicio en ese horario
    is_active = Column(Boolean, default=True)

    # Relaciones
    professional = relationship("User", back_populates="availability_slots")


class BlockedDate(Base):
    """
    Fechas bloqueadas para un profesional (vacaciones, incapacidades, etc.).
    """
    __tablename__ = "blocked_dates"

    id = Column(Integer, primary_key=True, index=True)
    professional_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blocked_date = Column(Date, nullable=False)
    reason = Column(String, nullable=True)
