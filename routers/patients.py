from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models.patient import Patient
from models.user import User
from models.appointment import Appointment, AppointmentStatus
from schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientSummary
from core.dependencies import require_any_staff, require_admin_or_receptionist

router = APIRouter(prefix="/patients", tags=["Pacientes"])


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar nuevo paciente")
def create_patient(
    body: PatientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_receptionist),
):
    """Registra un nuevo paciente en el sistema."""
    existing = db.query(Patient).filter(Patient.document_number == body.document_number).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un paciente con ese número de documento")

    patient = Patient(**body.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/", response_model=List[PatientSummary], summary="Buscar/listar pacientes")
def list_patients(
    search: Optional[str] = Query(None, description="Buscar por nombre o documento"),
    eps: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    """Lista pacientes con búsqueda opcional por nombre o documento. Incluye estado de cita."""
    query = db.query(Patient)

    if search:
        term = f"%{search}%"
        query = query.filter(
            (Patient.document_number.ilike(term))
            | (Patient.first_name.ilike(term))
            | (Patient.last_name.ilike(term))
        )
    if eps:
        query = query.filter(Patient.eps.ilike(f"%{eps}%"))

    patients = query.order_by(Patient.last_name, Patient.first_name).offset(skip).limit(limit).all()

    # Calcular has_appointment para cada paciente
    patient_ids = [p.id for p in patients]
    active_statuses = [
        AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS
    ]
    with_appt = set(
        row[0] for row in
        db.query(Appointment.patient_id)
        .filter(
            Appointment.patient_id.in_(patient_ids),
            Appointment.status.in_(active_statuses),
        )
        .distinct()
        .all()
    )

    result = []
    for p in patients:
        summary = PatientSummary.model_validate(p)
        summary.has_appointment = p.id in with_appt
        result.append(summary)
    return result


@router.get("/{patient_id}", response_model=PatientResponse, summary="Ver paciente por ID")
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


@router.get("/document/{document_number}", response_model=PatientResponse,
            summary="Buscar paciente por documento")
def get_patient_by_document(
    document_number: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    patient = db.query(Patient).filter(Patient.document_number == document_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


@router.patch("/{patient_id}", response_model=PatientResponse, summary="Actualizar datos del paciente")
def update_patient(
    patient_id: int,
    body: PatientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient
