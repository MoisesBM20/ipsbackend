from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from models.service import Service
from schemas.service import ServiceCreate, ServiceResponse
from core.dependencies import get_current_user, require_admin, require_any_staff

router = APIRouter(prefix="/services", tags=["Servicios"])

SEED_SERVICES = [
    "Atención Médica Domiciliaria",
    "Enfermería Domiciliaria",
    "Terapia Física",
    "Nutrición",
    "Psicología",
    "Atención Postquirúrgica",
    "Sueroterapia Ortomolecular",
]


def seed_default_services(db: Session) -> None:
    """Inserta los servicios iniciales si la tabla está vacía."""
    if db.query(Service).count() == 0:
        for name in SEED_SERVICES:
            db.add(Service(name=name))
        db.commit()


@router.get("/", response_model=List[ServiceResponse], summary="Listar servicios activos")
def list_services(
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    seed_default_services(db)
    return db.query(Service).filter(Service.is_active == True).order_by(Service.name).all()


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear nuevo servicio")
def create_service(
    body: ServiceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="El nombre no puede estar vacío")
    existing = db.query(Service).filter(Service.name == name).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=409, detail="Ya existe un servicio con ese nombre")
    service = Service(name=name)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", summary="Eliminar servicio")
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    service.is_active = False
    db.commit()
    return {"message": f"Servicio '{service.name}' eliminado correctamente"}
