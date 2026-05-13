from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from database import get_db
from models.appointment import Appointment, AppointmentStatus
from models.patient import Patient
from models.user import User, UserRole
from models.clinical_record import ClinicalRecord
from core.dependencies import require_any_staff

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", summary="Estadísticas generales del panel administrativo")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    """
    Retorna métricas clave para el panel principal:
    - Total pacientes registrados
    - Citas hoy / esta semana
    - Distribución de estados de citas
    - Empleados activos por rol
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Pacientes
    total_patients = db.query(func.count(Patient.id)).scalar()

    # Citas hoy
    today_total = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_date == today
    ).scalar()

    today_completed = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_date == today,
        Appointment.status == AppointmentStatus.COMPLETED,
    ).scalar()

    today_pending = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_date == today,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
    ).scalar()

    # Citas esta semana
    week_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_date >= week_start,
        Appointment.appointment_date <= week_end,
    ).scalar()

    # Citas por estado (total histórico)
    status_breakdown = db.query(
        Appointment.status, func.count(Appointment.id)
    ).group_by(Appointment.status).all()

    # Empleados activos por rol
    staff_by_role = db.query(
        User.role, func.count(User.id)
    ).filter(User.is_active == True).group_by(User.role).all()

    # Historias clínicas abiertas
    total_clinical_records = db.query(func.count(ClinicalRecord.id)).scalar()

    # Próximas citas (siguiente 7 días)
    upcoming = db.query(Appointment).filter(
        Appointment.appointment_date > today,
        Appointment.appointment_date <= today + timedelta(days=7),
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
    ).order_by(Appointment.appointment_date, Appointment.start_time).limit(10).all()

    upcoming_list = [
        {
            "id": a.id,
            "patient_name": f"{a.patient.first_name} {a.patient.last_name}" if a.patient else "N/A",
            "professional_name": a.professional.full_name if a.professional else "N/A",
            "date": str(a.appointment_date),
            "time": str(a.start_time),
            "type": a.appointment_type.value,
            "status": a.status.value,
        }
        for a in upcoming
    ]

    return {
        "patients": {
            "total": total_patients,
            "with_clinical_record": total_clinical_records,
        },
        "appointments": {
            "today_total": today_total,
            "today_completed": today_completed,
            "today_pending": today_pending,
            "this_week": week_appointments,
            "by_status": {s.value: count for s, count in status_breakdown},
        },
        "staff": {
            "by_role": {role.value: count for role, count in staff_by_role},
        },
        "upcoming_appointments": upcoming_list,
    }


@router.get("/appointments/by-day", summary="Citas agrupadas por día (para calendario)")
def get_appointments_by_day(
    date_from: date = Query(...),
    date_to: date = Query(...),
    professional_id: int = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    """Retorna el conteo de citas por día para renderizar el calendario."""
    query = db.query(
        Appointment.appointment_date,
        func.count(Appointment.id).label("total"),
    ).filter(
        Appointment.appointment_date >= date_from,
        Appointment.appointment_date <= date_to,
    )

    if professional_id:
        query = query.filter(Appointment.professional_id == professional_id)

    rows = query.group_by(Appointment.appointment_date).all()
    return {str(row.appointment_date): row.total for row in rows}
