import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from models.clinical_record import ClinicalRecord, ClinicalEntry
from models.patient import Patient
from models.user import User, UserRole
from schemas.clinical_record import (
    ClinicalEntryCreate, ClinicalEntryResponse, ClinicalRecordResponse
)
from core.dependencies import get_current_user, require_medical_staff, require_any_staff
from services.audit_service import log_action
from pydantic import BaseModel
from datetime import datetime


class ClinicalRecordSummary(BaseModel):
    id: int
    record_number: str
    patient_id: int
    patient_name: str
    patient_document: str
    patient_document_type: str
    total_entries: int
    opened_at: datetime

    model_config = {"from_attributes": True}

router = APIRouter(prefix="/clinical-records", tags=["Historias Clínicas"])


@router.get("/", response_model=List[ClinicalRecordSummary], summary="Listar historias clínicas")
def list_clinical_records(
    search: Optional[str] = Query(None, description="Buscar por nombre o documento del paciente"),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    query = db.query(ClinicalRecord).join(Patient, ClinicalRecord.patient_id == Patient.id)
    if search:
        term = f"%{search}%"
        query = query.filter(
            Patient.document_number.ilike(term)
            | Patient.first_name.ilike(term)
            | Patient.last_name.ilike(term)
        )
    records = query.order_by(ClinicalRecord.opened_at.desc()).all()
    return [
        ClinicalRecordSummary(
            id=r.id,
            record_number=r.record_number,
            patient_id=r.patient_id,
            patient_name=f"{r.patient.first_name} {r.patient.last_name}",
            patient_document=r.patient.document_number,
            patient_document_type=r.patient.document_type.value if hasattr(r.patient.document_type, 'value') else str(r.patient.document_type),
            total_entries=len(r.entries),
            opened_at=r.opened_at,
        )
        for r in records
    ]


def _generate_record_number(db: Session) -> str:
    """Genera un número de historia clínica único tipo HC-00001."""
    count = db.query(ClinicalRecord).count()
    return f"HC-{str(count + 1).zfill(5)}"


@router.post("/patients/{patient_id}", response_model=ClinicalRecordResponse,
             status_code=201, summary="Abrir Historia Clínica para un paciente")
def open_clinical_record(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Crea la Historia Clínica de un paciente (solo si no tiene una)."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    existing = db.query(ClinicalRecord).filter(ClinicalRecord.patient_id == patient_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="El paciente ya tiene una Historia Clínica")

    record = ClinicalRecord(
        patient_id=patient_id,
        record_number=_generate_record_number(db),
        opened_by=current_user.id,
    )
    db.add(record)
    db.flush()
    log_action(db, "abrir_hc", "historia_clinica",
               f"Se abrió la Historia Clínica {record.record_number} para {patient.first_name} {patient.last_name}",
               user=current_user, entity_id=record.id)
    db.commit()
    db.refresh(record)
    return record


@router.get("/patients/{patient_id}", response_model=ClinicalRecordResponse,
            summary="Ver Historia Clínica de un paciente")
def get_clinical_record(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    record = db.query(ClinicalRecord).filter(ClinicalRecord.patient_id == patient_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="No se encontró Historia Clínica para este paciente")

    entries = []
    for entry in record.entries:
        resp = ClinicalEntryResponse.model_validate(entry)
        if entry.professional:
            resp.professional_name = entry.professional.full_name
        entries.append(resp)

    return ClinicalRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        record_number=record.record_number,
        opened_by=record.opened_by,
        opened_at=record.opened_at,
        entries=entries,
    )


@router.get("/{record_id}", response_model=ClinicalRecordResponse, summary="Ver Historia Clínica por ID")
def get_clinical_record_by_id(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    record = db.query(ClinicalRecord).filter(ClinicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Historia Clínica no encontrada")
    return record


@router.post("/entries", response_model=ClinicalEntryResponse, status_code=201,
             summary="Agregar entrada a Historia Clínica")
def add_clinical_entry(
    body: ClinicalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """
    Agrega una nota/entrada a la Historia Clínica.
    Las entradas NUNCA se eliminan (trazabilidad médica).
    """
    record = db.query(ClinicalRecord).filter(ClinicalRecord.id == body.clinical_record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Historia Clínica no encontrada")

    # Serializar vital_signs a JSON si se proporcionan
    vital_signs_json = None
    if body.vital_signs:
        vital_signs_json = json.dumps(body.vital_signs.model_dump(exclude_none=True), ensure_ascii=False)

    entry = ClinicalEntry(
        clinical_record_id=body.clinical_record_id,
        professional_id=current_user.id,
        appointment_id=body.appointment_id,
        entry_type=body.entry_type,
        reason_for_visit=body.reason_for_visit,
        anamnesis=body.anamnesis,
        physical_exam=body.physical_exam,
        vital_signs=vital_signs_json,
        diagnosis_code=body.diagnosis_code,
        diagnosis_description=body.diagnosis_description,
        diagnosis_type=body.diagnosis_type,
        treatment_plan=body.treatment_plan,
        prescriptions=body.prescriptions,
        procedures_performed=body.procedures_performed,
        referral_destination=body.referral_destination,
        referral_reason=body.referral_reason,
        next_appointment_notes=body.next_appointment_notes,
        additional_notes=body.additional_notes,
    )
    db.add(entry)
    db.flush()
    patient = db.query(Patient).filter(Patient.id == record.patient_id).first()
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else f"paciente #{record.patient_id}"
    log_action(db, "nueva_entrada", "historia_clinica",
               f"Nueva entrada ({body.entry_type.value}) en HC de {patient_name} por {current_user.full_name}",
               user=current_user, entity_id=record.id)
    db.commit()
    db.refresh(entry)

    resp = ClinicalEntryResponse.model_validate(entry)
    resp.professional_name = current_user.full_name
    return resp


@router.get("/{record_id}/entries", summary="Ver todas las entradas de una Historia Clínica")
def get_entries(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    """Retorna todas las entradas de una HC ordenadas por fecha descendente."""
    record = db.query(ClinicalRecord).filter(ClinicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Historia Clínica no encontrada")

    entries = []
    for entry in record.entries:
        resp = ClinicalEntryResponse.model_validate(entry)
        if entry.professional:
            resp.professional_name = entry.professional.full_name
        entries.append(resp)
    return entries
