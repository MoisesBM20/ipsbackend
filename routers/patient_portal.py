"""
Portal del paciente: endpoints exclusivos para el rol 'paciente'.
Solo puede ver y gestionar sus propias citas.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel
from database import get_db
from models.appointment import Appointment, AppointmentStatus, AppointmentType
from models.patient import Patient
from models.user import User
from schemas.appointment import AppointmentResponse
from core.dependencies import get_current_user
from core.security import verify_password, hash_password
from services.scheduler_service import get_available_slots, calculate_end_time
from services.audit_service import log_action
from schemas.auth import PatientProfileUpdate

router = APIRouter(prefix="/portal", tags=["Portal Paciente"])


class PortalBookingRequest(BaseModel):
    professional_id: int
    appointment_date: date
    start_time: str
    appointment_type: AppointmentType
    reason: Optional[str] = None


def _require_patient(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role.value != "paciente":
        raise HTTPException(status_code=403, detail="Acceso solo para pacientes")
    return current_user


def _enrich(appt: Appointment) -> AppointmentResponse:
    resp = AppointmentResponse.model_validate(appt)
    if appt.patient:
        resp.patient_name = f"{appt.patient.first_name} {appt.patient.last_name}"
        resp.patient_document = appt.patient.document_number
    if appt.professional:
        resp.professional_name = appt.professional.full_name
    return resp


@router.get("/my-appointments", response_model=List[AppointmentResponse],
            summary="Mis citas (portal paciente)")
def get_my_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_patient),
):
    """Retorna todas las citas del paciente autenticado."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return []
    appointments = (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.appointment_date.desc(), Appointment.start_time)
        .all()
    )
    return [_enrich(a) for a in appointments]


@router.get("/me", summary="Perfil del paciente autenticado")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_patient),
):
    """Retorna los datos del paciente vinculados al usuario."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Perfil de paciente no encontrado")
    return {
        "id": patient.id,
        "full_name": f"{patient.first_name} {patient.last_name}",
        "document_type": patient.document_type,
        "document_number": patient.document_number,
        "birth_date": str(patient.birth_date),
        "gender": patient.gender,
        "phone": patient.phone,
        "email": patient.email,
        "eps": patient.eps,
        "regime": patient.regime,
    }


@router.patch("/profile", summary="Actualizar perfil del paciente")
def update_patient_profile(
    body: PatientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_patient),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Perfil de paciente no encontrado")

    if body.phone is not None:      patient.phone = body.phone or None
    if body.email is not None:      patient.email = body.email or None
    if body.address is not None:    patient.address = body.address or None
    if body.city is not None:       patient.city = body.city or None
    if body.eps is not None:        patient.eps = body.eps or None
    if body.regime is not None:     patient.regime = body.regime or None
    if body.emergency_contact_name is not None:         patient.emergency_contact_name = body.emergency_contact_name or None
    if body.emergency_contact_phone is not None:        patient.emergency_contact_phone = body.emergency_contact_phone or None
    if body.emergency_contact_relationship is not None: patient.emergency_contact_relationship = body.emergency_contact_relationship or None

    # Cambio de contraseña opcional
    if body.new_password:
        if not body.current_password:
            raise HTTPException(status_code=400, detail="Debes ingresar tu contraseña actual")
        if not verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
        if len(body.new_password) < 6:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")
        current_user.password_hash = hash_password(body.new_password)

    log_action(db, "actualizar", "paciente", f"Paciente {patient.first_name} {patient.last_name} actualizó su perfil", user=current_user, entity_id=patient.id)
    db.commit()
    return {"message": "Perfil actualizado correctamente"}


@router.post("/book-appointment", summary="Solicitar cita desde el portal")
def book_portal_appointment(
    body: PortalBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_patient),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Perfil de paciente no encontrado")

    if body.appointment_date < date.today():
        raise HTTPException(status_code=400, detail="No se pueden agendar citas en fechas pasadas")

    professional = db.query(User).filter(
        User.id == body.professional_id, User.is_active == True
    ).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    availability = get_available_slots(db, body.professional_id, professional.full_name, body.appointment_date)
    requested_slot = next((s for s in availability.slots if s.start_time == body.start_time), None)
    if not requested_slot:
        raise HTTPException(status_code=400, detail="Horario no disponible para ese día")
    if not requested_slot.is_available:
        raise HTTPException(status_code=409, detail="El horario ya fue tomado. Por favor elige otro.")

    try:
        start_time_obj = datetime.strptime(body.start_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")

    end_time_obj = calculate_end_time(start_time_obj, body.professional_id, body.appointment_date, db)

    appointment = Appointment(
        patient_id=patient.id,
        professional_id=body.professional_id,
        appointment_date=body.appointment_date,
        start_time=start_time_obj,
        end_time=end_time_obj,
        appointment_type=body.appointment_type,
        reason=body.reason,
        notes="Agendado desde portal del paciente",
        status=AppointmentStatus.SCHEDULED,
        created_by=current_user.id,
    )
    db.add(appointment)
    log_action(
        db, "agendar_cita", "cita",
        f"Paciente {patient.first_name} {patient.last_name} agendó cita con {professional.full_name} "
        f"para el {body.appointment_date.strftime('%d/%m/%Y')} a las {body.start_time}",
        user=current_user, entity_id=None,
    )
    db.commit()
    db.refresh(appointment)

    return {
        "id": appointment.id,
        "confirmation_code": f"IPS-{appointment.id:06d}",
        "appointment_date": str(appointment.appointment_date),
        "start_time": str(appointment.start_time)[:5],
        "end_time": str(appointment.end_time)[:5],
        "professional_name": professional.full_name,
        "appointment_type": appointment.appointment_type.value,
        "message": f"Cita agendada para el {appointment.appointment_date.strftime('%d/%m/%Y')} a las {str(appointment.start_time)[:5]} con {professional.full_name}",
    }
