from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import time, date
from models.availability import DayOfWeek


class AvailabilitySlotCreate(BaseModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    slot_duration_minutes: int = 30
    service_type: Optional[str] = None

    @model_validator(mode="after")
    def end_after_start(self) -> "AvailabilitySlotCreate":
        if self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self


class AvailabilitySlotResponse(BaseModel):
    id: int
    professional_id: int
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    slot_duration_minutes: int
    service_type: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class BlockedDateCreate(BaseModel):
    professional_id: int
    blocked_date: date
    reason: Optional[str] = None


class BlockedDateResponse(BaseModel):
    id: int
    professional_id: int
    blocked_date: date
    reason: Optional[str]

    model_config = {"from_attributes": True}


class TimeSlot(BaseModel):
    """Un slot de tiempo disponible para agendar."""
    start_time: str   # "08:00"
    end_time: str     # "08:30"
    is_available: bool


class DayAvailability(BaseModel):
    """Disponibilidad de un profesional para un día específico."""
    date: date
    professional_id: int
    professional_name: str
    slots: List[TimeSlot]
