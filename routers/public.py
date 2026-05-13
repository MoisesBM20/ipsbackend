"""
Endpoints PÚBLICOS — no requieren autenticación.

Usados por el sitio web de la IPS para que pacientes externos
puedan consultar disponibilidad y agendar citas sin tener cuenta.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
from pydantic import BaseModel, EmailStr

from database import get_db
from models.patient import Patient, DocumentType, Gender
from models.appointment import Appointment, AppointmentStatus, AppointmentType
from models.user import User, UserRole
from models.availability import AvailabilitySlot
from services.scheduler_service import get_available_slots, calculate_end_time
from schemas.availability import DayAvailability

router = APIRouter(prefix="/public", tags=["Agendamiento Público"])


# ── Schemas exclusivos para el flujo público ────────────────────────────────

class PublicPatientInfo(BaseModel):
    """Datos del paciente al agendar desde el sitio web."""
    document_type: DocumentType
    document_number: str
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    phone: str
    email: Optional[EmailStr] = None
    eps: Optional[str] = None


class PublicAppointmentRequest(BaseModel):
    """Solicitud de cita desde el sitio público."""
    patient: PublicPatientInfo
    professional_id: int
    appointment_date: date
    start_time: str            # "08:00"
    appointment_type: AppointmentType
    reason: Optional[str] = None


class PublicAppointmentResponse(BaseModel):
    appointment_id: int
    confirmation_code: str
    patient_name: str
    professional_name: str
    appointment_date: date
    start_time: str
    end_time: str
    appointment_type: str
    status: str
    message: str


class ServiceInfo(BaseModel):
    """Información de un servicio disponible para agendar."""
    service_type: AppointmentType
    display_name: str
    description: str
    professionals: List[dict]


# Nombres legibles para el frontend
SERVICE_DISPLAY = {
    AppointmentType.CONSULTATION: ("Consulta Médica General", "Evaluación médica domiciliaria o presencial"),
    AppointmentType.NURSING: ("Enfermería Domiciliaria", "Atención de enfermería en tu hogar"),
    AppointmentType.PHYSICAL_THERAPY: ("Terapia Física", "Rehabilitación y terapia física"),
    AppointmentType.NUTRITION: ("Nutrición", "Consulta nutricional personalizada"),
    AppointmentType.PSYCHOLOGY: ("Psicología", "Atención psicológica profesional"),
    AppointmentType.POST_SURGICAL: ("Atención Post-quirúrgica", "Cuidados especializados post-operación"),
    AppointmentType.SEROTHERAPY: ("Sueroterapia", "Terapia intravenosa especializada"),
    AppointmentType.FOLLOW_UP: ("Control y Seguimiento", "Seguimiento de tratamiento en curso"),
}


# ── Servicios disponibles ────────────────────────────────────────────────────

@router.get("/services", summary="Listar servicios disponibles para agendar")
def get_available_services(db: Session = Depends(get_db)) -> List[ServiceInfo]:
    """
    Retorna los servicios activos con los profesionales que los atienden.
    Se usa para poblar el formulario de agendamiento en el sitio web.
    """
    # Buscar qué tipos de servicio tienen slots activos configurados
    active_slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.is_active == True
    ).all()

    # Agrupar profesionales por tipo de servicio
    service_professionals: dict[str, set[int]] = {}
    for slot in active_slots:
        svc = slot.service_type or "consulta_medica"
        service_professionals.setdefault(svc, set()).add(slot.professional_id)

    services = []
    for svc_key, prof_ids in service_professionals.items():
        try:
            svc_enum = AppointmentType(svc_key)
        except ValueError:
            svc_enum = AppointmentType.CONSULTATION

        display_name, description = SERVICE_DISPLAY.get(
            svc_enum, (svc_key.replace("_", " ").title(), "")
        )

        professionals = db.query(User).filter(
            User.id.in_(prof_ids),
            User.is_active == True,
        ).all()

        services.append(ServiceInfo(
            service_type=svc_enum,
            display_name=display_name,
            description=description,
            professionals=[
                {"id": p.id, "name": p.full_name, "specialty": p.specialty}
                for p in professionals
            ],
        ))

    return services


@router.get(
    "/availability",
    response_model=List[DayAvailability],
    summary="Consultar disponibilidad por servicio y rango de fechas",
)
def get_public_availability(
    professional_id: int = Query(..., description="ID del profesional"),
    date_from: date = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD). Máx 30 días"),
    db: Session = Depends(get_db),
):
    """
    Retorna los slots disponibles (libres y ocupados) para el profesional
    en el rango de fechas indicado. No requiere autenticación.
    """
    if date_from < date.today():
        raise HTTPException(status_code=400, detail="No se pueden consultar fechas pasadas")

    if date_to is None:
        date_to = date_from + timedelta(days=13)  # 2 semanas por defecto

    if (date_to - date_from).days > 30:
        raise HTTPException(status_code=400, detail="El rango máximo es de 30 días")

    professional = db.query(User).filter(
        User.id == professional_id, User.is_active == True
    ).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    result = []
    current = date_from
    while current <= date_to:
        day_data = get_available_slots(db, professional_id, professional.full_name, current)
        # Solo incluir días con al menos un slot disponible
        if any(s.is_available for s in day_data.slots):
            result.append(day_data)
        current += timedelta(days=1)

    return result


# ── Agendar cita pública ────────────────────────────────────────────────────

@router.post(
    "/appointments",
    response_model=PublicAppointmentResponse,
    status_code=201,
    summary="Agendar cita desde el sitio web (sin login)",
)
def book_public_appointment(
    body: PublicAppointmentRequest,
    db: Session = Depends(get_db),
):
    """
    Permite a un paciente externo agendar una cita.

    Flujo:
    1. Busca el paciente por número de documento.
    2. Si no existe, lo crea automáticamente con los datos proporcionados.
    3. Verifica que el slot esté disponible.
    4. Crea la cita con estado "agendada".
    """
    from datetime import datetime

    # ── 1. Resolver paciente ─────────────────────────────────────────────────
    patient = db.query(Patient).filter(
        Patient.document_number == body.patient.document_number
    ).first()

    if not patient:
        patient = Patient(
            document_type=body.patient.document_type,
            document_number=body.patient.document_number,
            first_name=body.patient.first_name,
            last_name=body.patient.last_name,
            birth_date=body.patient.birth_date,
            gender=body.patient.gender,
            phone=body.patient.phone,
            email=body.patient.email,
            eps=body.patient.eps,
        )
        db.add(patient)
        db.flush()  # obtener el ID sin commit aún
    else:
        # Actualizar datos de contacto si cambió algo
        if body.patient.phone:
            patient.phone = body.patient.phone
        if body.patient.email:
            patient.email = body.patient.email

    # ── 2. Validar fecha futura ──────────────────────────────────────────────
    if body.appointment_date < date.today():
        raise HTTPException(status_code=400, detail="No se pueden agendar citas en fechas pasadas")

    # ── 3. Verificar profesional ─────────────────────────────────────────────
    professional = db.query(User).filter(
        User.id == body.professional_id, User.is_active == True
    ).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    # ── 4. Verificar disponibilidad ──────────────────────────────────────────
    availability = get_available_slots(
        db, body.professional_id, professional.full_name, body.appointment_date
    )
    requested_slot = next(
        (s for s in availability.slots if s.start_time == body.start_time),
        None,
    )
    if not requested_slot:
        raise HTTPException(
            status_code=400,
            detail="El horario seleccionado no está dentro de la disponibilidad del profesional",
        )
    if not requested_slot.is_available:
        raise HTTPException(
            status_code=409,
            detail="El horario ya fue tomado. Por favor elige otro.",
        )

    # ── 5. Parsear hora de inicio ────────────────────────────────────────────
    try:
        h, m = body.start_time.split(":")
        start_time_obj = datetime.strptime(body.start_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Use HH:MM")

    end_time_obj = calculate_end_time(start_time_obj, body.professional_id, body.appointment_date, db)

    # ── 6. Crear la cita ─────────────────────────────────────────────────────
    # Buscar el usuario admin/sistema para registrar como creador
    system_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
    creator_id = system_user.id if system_user else 1

    appointment = Appointment(
        patient_id=patient.id,
        professional_id=body.professional_id,
        appointment_date=body.appointment_date,
        start_time=start_time_obj,
        end_time=end_time_obj,
        appointment_type=body.appointment_type,
        reason=body.reason,
        notes="Agendado desde el sitio web",
        status=AppointmentStatus.SCHEDULED,
        created_by=creator_id,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # ── 7. Generar código de confirmación ────────────────────────────────────
    confirmation_code = f"IPS-{appointment.id:06d}"

    return PublicAppointmentResponse(
        appointment_id=appointment.id,
        confirmation_code=confirmation_code,
        patient_name=f"{patient.first_name} {patient.last_name}",
        professional_name=professional.full_name,
        appointment_date=body.appointment_date,
        start_time=requested_slot.start_time,
        end_time=requested_slot.end_time,
        appointment_type=body.appointment_type.value,
        status=AppointmentStatus.SCHEDULED.value,
        message=(
            f"✅ Cita confirmada. Tu código de confirmación es {confirmation_code}. "
            f"Te esperamos el {body.appointment_date.strftime('%d/%m/%Y')} "
            f"a las {body.start_time}."
        ),
    )


@router.get(
    "/appointments/{confirmation_code}",
    summary="Consultar estado de una cita por código de confirmación",
)
def get_appointment_by_code(
    confirmation_code: str,
    db: Session = Depends(get_db),
):
    """Permite al paciente verificar su cita con el código recibido."""
    try:
        appt_id = int(confirmation_code.replace("IPS-", ""))
    except ValueError:
        raise HTTPException(status_code=400, detail="Código de confirmación inválido")

    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    return {
        "confirmation_code": confirmation_code,
        "patient_name": f"{appt.patient.first_name} {appt.patient.last_name}" if appt.patient else "N/A",
        "professional_name": appt.professional.full_name if appt.professional else "N/A",
        "appointment_date": str(appt.appointment_date),
        "start_time": str(appt.start_time)[:5],
        "end_time": str(appt.end_time)[:5],
        "appointment_type": appt.appointment_type.value,
        "status": appt.status.value,
    }
