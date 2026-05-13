from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from database import Base


class EntryType(str, Enum):
    CONSULTATION = "consulta"
    NURSING_NOTE = "nota_enfermeria"
    EVOLUTION = "evolucion"
    PROCEDURE = "procedimiento"
    MEDICATION = "medicamento"
    LAB_RESULT = "resultado_laboratorio"
    IMAGING = "imagen_diagnostica"
    REFERRAL = "remision"
    DISCHARGE = "egreso"


class ClinicalRecord(Base):
    """
    Historia Clínica del paciente. Una por paciente.
    Contiene metadatos y se relaciona con múltiples entradas (notas).
    """
    __tablename__ = "clinical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), unique=True, nullable=False)
    record_number = Column(String, unique=True, nullable=False)  # Número de HC

    # Apertura
    opened_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    patient = relationship("Patient", back_populates="clinical_record")
    opener = relationship("User", foreign_keys=[opened_by])
    entries = relationship("ClinicalEntry", back_populates="clinical_record", order_by="ClinicalEntry.entry_date.desc()")


class ClinicalEntry(Base):
    """
    Entrada individual en la Historia Clínica.
    Cada consulta, procedimiento, nota de enfermería, etc.
    """
    __tablename__ = "clinical_entries"

    id = Column(Integer, primary_key=True, index=True)
    clinical_record_id = Column(Integer, ForeignKey("clinical_records.id"), nullable=False)
    professional_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)

    # Clasificación
    entry_type = Column(SAEnum(EntryType), nullable=False)
    entry_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Contenido clínico
    reason_for_visit = Column(Text, nullable=True)      # Motivo de consulta
    anamnesis = Column(Text, nullable=True)              # Historia actual
    physical_exam = Column(Text, nullable=True)          # Examen físico
    vital_signs = Column(Text, nullable=True)            # Signos vitales (JSON string)

    # Diagnóstico (CIE-10)
    diagnosis_code = Column(String, nullable=True)       # Ej: J00, K30
    diagnosis_description = Column(Text, nullable=True)
    diagnosis_type = Column(String, nullable=True)       # Confirmado, Presuntivo

    # Tratamiento
    treatment_plan = Column(Text, nullable=True)
    prescriptions = Column(Text, nullable=True)          # Medicamentos (JSON)
    procedures_performed = Column(Text, nullable=True)   # Procedimientos (JSON)

    # Remisión
    referral_destination = Column(String, nullable=True)
    referral_reason = Column(Text, nullable=True)

    # Seguimiento
    next_appointment_notes = Column(Text, nullable=True)
    additional_notes = Column(Text, nullable=True)

    # Auditoría (la historia clínica no se elimina, solo se audita)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    clinical_record = relationship("ClinicalRecord", back_populates="entries")
    professional = relationship("User", back_populates="clinical_entries")
