from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_db
from models.appointment import Appointment, AppointmentStatus
from models.patient import Patient
from models.user import User
from schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse, CalendarDay
from services.scheduler_service import get_available_slots, calculate_end_time
from core.dependencies import get_current_user, require_any_staff, require_admin_or_receptionist
from services.audit_service import log_action

router = APIRouter(prefix="/appointments", tags=["Citas"])


def _enrich_appointment(appt: Appointment) -> AppointmentResponse:
    """Agrega nombre de paciente y profesional al response."""
    resp = AppointmentResponse.model_validate(appt)
    if appt.patient:
        resp.patient_name = f"{appt.patient.first_name} {appt.patient.last_name}"
        resp.patient_document = appt.patient.document_number
    if appt.professional:
        resp.professional_name = appt.professional.full_name
    return resp


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED,
             summary="Agendar cita")
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    """
    Agenda una cita verificando disponibilidad del profesional.
    Valida que el slot esté libre y no sea en el pasado.
    """
    # Verificar paciente
    patient = db.query(Patient).filter(Patient.id == body.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Verificar profesional
    professional = db.query(User).filter(User.id == body.professional_id, User.is_active == True).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    # Verificar disponibilidad del slot
    availability = get_available_slots(
        db, body.professional_id, professional.full_name, body.appointment_date
    )
    requested_slot = next(
        (s for s in availability.slots if s.start_time == body.start_time.strftime("%H:%M")),
        None,
    )
    if not requested_slot:
        raise HTTPException(status_code=400, detail="El horario solicitado no está en la disponibilidad del profesional")
    if not requested_slot.is_available:
        raise HTTPException(status_code=409, detail="El horario ya está ocupado")

    # Calcular hora de fin
    end_time = calculate_end_time(body.start_time, body.professional_id, body.appointment_date, db)

    appointment = Appointment(
        patient_id=body.patient_id,
        professional_id=body.professional_id,
        appointment_date=body.appointment_date,
        start_time=body.start_time,
        end_time=end_time,
        appointment_type=body.appointment_type,
        reason=body.reason,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(appointment)
    db.flush()
    log_action(db, "crear", "cita",
               f"Cita agendada para {patient.first_name} {patient.last_name} el {body.appointment_date} a las {body.start_time} con {professional.full_name}",
               user=current_user, entity_id=appointment.id)
    db.commit()
    db.refresh(appointment)
    return _enrich_appointment(appointment)


@router.get("/", response_model=List[AppointmentResponse], summary="Listar citas con filtros")
def list_appointments(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    professional_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    document_number: Optional[str] = Query(None, description="Buscar por cédula del paciente"),
    status_filter: Optional[AppointmentStatus] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    """Filtra citas por rango de fechas, profesional, paciente, cédula y/o estado."""
    from models.user import UserRole

    query = db.query(Appointment).join(Patient, Appointment.patient_id == Patient.id)

    # Doctores y enfermeros solo ven sus propias citas
    if current_user.role in (UserRole.DOCTOR, UserRole.NURSE):
        query = query.filter(Appointment.professional_id == current_user.id)
    elif professional_id:
        query = query.filter(Appointment.professional_id == professional_id)

    if document_number:
        query = query.filter(Patient.document_number.ilike(f"%{document_number}%"))
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    if date_from:
        query = query.filter(Appointment.appointment_date >= date_from)
    if date_to:
        query = query.filter(Appointment.appointment_date <= date_to)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    appointments = query.order_by(
        Appointment.appointment_date.desc(), Appointment.start_time.desc()
    ).offset(skip).limit(limit).all()

    return [_enrich_appointment(a) for a in appointments]


@router.get("/today", response_model=CalendarDay, summary="Citas del día de hoy")
def get_todays_appointments(
    professional_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    from models.user import UserRole
    from datetime import date as today_date

    today = today_date.today()
    query = db.query(Appointment).filter(Appointment.appointment_date == today)

    if current_user.role in (UserRole.DOCTOR, UserRole.NURSE):
        query = query.filter(Appointment.professional_id == current_user.id)
    elif professional_id:
        query = query.filter(Appointment.professional_id == professional_id)

    appointments = query.order_by(Appointment.start_time).all()
    enriched = [_enrich_appointment(a) for a in appointments]

    return CalendarDay(date=today, appointments=enriched, total=len(enriched))


@router.get("/{appointment_id}", response_model=AppointmentResponse, summary="Ver cita por ID")
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return _enrich_appointment(appt)


@router.patch("/{appointment_id}", response_model=AppointmentResponse, summary="Actualizar cita")
def update_appointment(
    appointment_id: int,
    body: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    if body.status == AppointmentStatus.CANCELLED and not body.cancellation_reason:
        raise HTTPException(status_code=400, detail="Debe indicar el motivo de cancelación")

    data = body.model_dump(exclude_none=True)

    # Si se reprograma, recalcular end_time
    if any(k in data for k in ("professional_id", "appointment_date", "start_time")):
        new_prof_id = data.get("professional_id", appt.professional_id)
        new_date = data.get("appointment_date", appt.appointment_date)
        new_start = data.get("start_time", appt.start_time)
        data["end_time"] = calculate_end_time(new_start, new_prof_id, new_date, db)

    for field, value in data.items():
        setattr(appt, field, value)

    patient_name = f"{appt.patient.first_name} {appt.patient.last_name}" if appt.patient else f"cita #{appt.id}"
    if body.status and body.status == AppointmentStatus.IN_PROGRESS:
        action_desc = f"Cita en atención para {patient_name}"
        action = "atender"
    else:
        action_desc = f"Cita actualizada para {patient_name}"
        action = "actualizar"
    log_action(db, action, "cita", action_desc, user=current_user, entity_id=appt.id)
    db.commit()
    db.refresh(appt)
    return _enrich_appointment(appt)


@router.delete("/{appointment_id}", summary="Cancelar cita")
def cancel_appointment(
    appointment_id: int,
    reason: str = Query(..., description="Motivo de cancelación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    appt.status = AppointmentStatus.CANCELLED
    appt.cancellation_reason = reason
    patient_name = f"{appt.patient.first_name} {appt.patient.last_name}" if appt.patient else f"cita #{appointment_id}"
    log_action(db, "cancelar", "cita",
               f"Cita cancelada para {patient_name}. Motivo: {reason}",
               user=current_user, entity_id=appointment_id)
    db.commit()
    return {"message": "Cita cancelada"}
