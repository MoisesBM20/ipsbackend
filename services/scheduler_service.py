from datetime import date, time, timedelta, datetime
from typing import List
from sqlalchemy.orm import Session
from models.availability import AvailabilitySlot, BlockedDate, DayOfWeek
from models.appointment import Appointment, AppointmentStatus
from schemas.availability import TimeSlot, DayAvailability

# Mapeo de nombre de día a número ISO (lunes=0, domingo=6)
DAY_MAP = {
    DayOfWeek.MONDAY: 0,
    DayOfWeek.TUESDAY: 1,
    DayOfWeek.WEDNESDAY: 2,
    DayOfWeek.THURSDAY: 3,
    DayOfWeek.FRIDAY: 4,
    DayOfWeek.SATURDAY: 5,
    DayOfWeek.SUNDAY: 6,
}


def get_available_slots(
    db: Session,
    professional_id: int,
    professional_name: str,
    target_date: date,
) -> DayAvailability:
    """
    Calcula los slots disponibles de un profesional para una fecha dada.
    Considera:
    1. La disponibilidad semanal parametrizada (AvailabilitySlot)
    2. Las fechas bloqueadas (BlockedDate)
    3. Las citas ya agendadas (Appointment)
    """
    slots: List[TimeSlot] = []

    # Verificar si la fecha está bloqueada
    is_blocked = db.query(BlockedDate).filter(
        BlockedDate.professional_id == professional_id,
        BlockedDate.blocked_date == target_date,
    ).first()

    if is_blocked:
        return DayAvailability(
            date=target_date,
            professional_id=professional_id,
            professional_name=professional_name,
            slots=[],
        )

    # Obtener la disponibilidad semanal para ese día de la semana
    day_iso = target_date.weekday()  # 0=lunes, 6=domingo
    target_day_enum = next(
        (day for day, iso in DAY_MAP.items() if iso == day_iso), None
    )

    if target_day_enum is None:
        return DayAvailability(date=target_date, professional_id=professional_id,
                               professional_name=professional_name, slots=[])

    availability_rows = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.professional_id == professional_id,
        AvailabilitySlot.day_of_week == target_day_enum,
        AvailabilitySlot.is_active == True,
    ).all()

    if not availability_rows:
        return DayAvailability(date=target_date, professional_id=professional_id,
                               professional_name=professional_name, slots=[])

    # Obtener citas ya agendadas ese día
    existing_appointments = db.query(Appointment).filter(
        Appointment.professional_id == professional_id,
        Appointment.appointment_date == target_date,
        Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]),
    ).all()

    occupied_starts = {appt.start_time for appt in existing_appointments}

    # Generar slots para cada rango de disponibilidad
    for avail in availability_rows:
        current = datetime.combine(target_date, avail.start_time)
        end = datetime.combine(target_date, avail.end_time)
        delta = timedelta(minutes=avail.slot_duration_minutes)

        while current + delta <= end:
            slot_start = current.time()
            slot_end = (current + delta).time()
            slots.append(TimeSlot(
                start_time=slot_start.strftime("%H:%M"),
                end_time=slot_end.strftime("%H:%M"),
                is_available=slot_start not in occupied_starts,
            ))
            current += delta

    return DayAvailability(
        date=target_date,
        professional_id=professional_id,
        professional_name=professional_name,
        slots=slots,
    )


def calculate_end_time(start_time: time, professional_id: int, target_date: date, db: Session) -> time:
    """Calcula la hora de fin de una cita según la duración del slot del profesional."""
    day_iso = target_date.weekday()
    target_day_enum = next((day for day, iso in DAY_MAP.items() if iso == day_iso), None)

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.professional_id == professional_id,
        AvailabilitySlot.day_of_week == target_day_enum,
        AvailabilitySlot.is_active == True,
    ).first()

    duration = slot.slot_duration_minutes if slot else 30
    dt = datetime.combine(target_date, start_time)
    return (dt + timedelta(minutes=duration)).time()
