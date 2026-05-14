from pydantic import BaseModel
from datetime import datetime


class ServiceCreate(BaseModel):
    name: str


class ServiceResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
