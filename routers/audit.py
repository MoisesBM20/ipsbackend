from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
from models.audit_log import AuditLog
from models.user import User
from pydantic import BaseModel
from core.dependencies import require_any_staff

router = APIRouter(prefix="/audit", tags=["Auditoría"])


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_name: Optional[str]
    user_role: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[int]
    description: str
    timestamp: datetime

    model_config = {"from_attributes": True}


@router.get("/logs", response_model=List[AuditLogResponse], summary="Registro de actividad")
def list_audit_logs(
    search: Optional[str] = Query(None, description="Buscar en descripción o usuario"),
    entity_type: Optional[str] = Query(None, description="Filtrar por tipo de entidad"),
    limit: int = Query(200, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if search:
        term = f"%{search}%"
        query = query.filter(
            AuditLog.description.ilike(term) | AuditLog.user_name.ilike(term)
        )
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
