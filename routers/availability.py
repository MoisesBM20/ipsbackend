from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta
from database import get_db
from models.availability import AvailabilitySlot, BlockedDate
from models.user import User, UserRole
from schemas.availability import (
    AvailabilitySlotCreate, AvailabilitySlotResponse,
    BlockedDateCreate, BlockedDateResponse, DayAvailability,
)
from services.scheduler_service import get_available_slots
from core.dependencies import get_current_user, require_any_staff, require_admin

router = APIRouter(prefix="/availability", tags=["Disponibilidad"])


# ── Configuración de slots semanales ────────────────────────────────────────

@router.post("/{professional_id}/slots", response_model=AvailabilitySlotResponse,
             status_code=201, summary="Agregar slot de disponibilidad semanal")
def add_availability_slot(
    professional_id: int,
    body: AvailabilitySlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin puede configurar disponibilidad de cualquier profesional.
    Un doctor/enfermero puede configurar la suya propia.
    """
    if current_user.role != UserRole.ADMIN and current_user.id != professional_id:
        raise HTTPException(status_code=403, detail="Sin permiso para editar la disponibilidad de otro profesional")

    # Verificar que no se solape con un slot existente del mismo día
    existing = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.professional_id == professional_id,
        AvailabilitySlot.day_of_week == body.day_of_week,
        AvailabilitySlot.is_active == True,
    ).all()

    for slot in existing:
        if not (body.end_time <= slot.start_time or body.start_time >= slot.end_time):
            raise HTTPException(
                status_code=409,
                detail=f"El horario se solapa con un slot existente ({slot.start_time} - {slot.end_time})"
            )

    new_slot = AvailabilitySlot(
        professional_id=professional_id,
        **body.model_dump(),
    )
    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)
    return new_slot


@router.get("/{professional_id}/slots", response_model=List[AvailabilitySlotResponse],
            summary="Ver disponibilidad semanal de un profesional")
def get_availability_slots(
    professional_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    return db.query(AvailabilitySlot).filter(
        AvailabilitySlot.professional_id == professional_id,
        AvailabilitySlot.is_active == True,
    ).order_by(AvailabilitySlot.day_of_week, AvailabilitySlot.start_time).all()


@router.delete("/{professional_id}/slots/{slot_id}", summary="Eliminar slot de disponibilidad")
def delete_availability_slot(
    professional_id: int,
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN and current_user.id != professional_id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id,
        AvailabilitySlot.professional_id == professional_id,
    ).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot no encontrado")

    slot.is_active = False
    db.commit()
    return {"message": "Slot eliminado"}


# ── Fechas bloqueadas ────────────────────────────────────────────────────────

@router.post("/blocked-dates", response_model=BlockedDateResponse, status_code=201,
             summary="Bloquear una fecha para un profesional")
def block_date(
    body: BlockedDateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN and current_user.id != body.professional_id:
        raise HTTPException(status_code=403, detail="Sin permiso")

    blocked = BlockedDate(**body.model_dump())
    db.add(blocked)
    db.commit()
    db.refresh(blocked)
    return blocked


@router.get("/{professional_id}/blocked-dates", response_model=List[BlockedDateResponse],
            summary="Ver fechas bloqueadas")
def get_blocked_dates(
    professional_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    return db.query(BlockedDate).filter(
        BlockedDate.professional_id == professional_id
    ).order_by(BlockedDate.blocked_date).all()


# ── Consulta de disponibilidad por fecha ────────────────────────────────────

@router.get("/{professional_id}/calendar", response_model=List[DayAvailability],
            summary="Ver slots disponibles para un rango de fechas")
def get_calendar(
    professional_id: int,
    start_date: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    """
    Retorna los slots disponibles y ocupados para cada día del rango.
    Ideal para renderizar un calendario visual en el frontend.
    """
    if (end_date - start_date).days > 31:
        raise HTTPException(status_code=400, detail="El rango máximo es de 31 días")

    professional = db.query(User).filter(User.id == professional_id).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    result = []
    current = start_date
    while current <= end_date:
        day_availability = get_available_slots(
            db, professional_id, professional.full_name, current
        )
        result.append(day_availability)
        current += timedelta(days=1)

    return result
