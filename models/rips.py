from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from database import Base


class RIPSStatus(str, Enum):
    DRAFT = "borrador"
    GENERATED = "generado"
    SUBMITTED = "enviado"
    ACCEPTED = "aceptado"
    REJECTED = "rechazado"


class RIPSReport(Base):
    """
    Reporte RIPS 2.0 generado para un período.
    RIPS = Registro Individual de Prestación de Servicios de Salud.
    """
    __tablename__ = "rips_reports"

    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(SAEnum(RIPSStatus), default=RIPSStatus.DRAFT)

    # Contenido JSON del reporte
    report_json = Column(Text, nullable=True)    # JSON completo RIPS 2.0

    # Estadísticas del reporte
    total_patients = Column(Integer, default=0)
    total_consultations = Column(Integer, default=0)
    total_procedures = Column(Integer, default=0)

    # Auditoría
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Relación
    generator = relationship("User", foreign_keys=[generated_by])
