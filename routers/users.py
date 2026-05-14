from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User, UserRole
from schemas.user import UserCreate, UserUpdate, UserResponse, UserSummary
from core.security import hash_password
from core.dependencies import get_current_user, require_admin, require_any_staff

router = APIRouter(prefix="/users", tags=["Usuarios / Empleados"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear nuevo empleado")
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Solo el ADMIN puede registrar nuevos empleados."""
    existing = db.query(User).filter(
        (User.email == body.email) | (User.document_number == body.document_number)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email o documento")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        document_number=body.document_number,
        phone=body.phone,
        role=body.role,
        specialty=body.specialty,
        registration_number=body.registration_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=List[UserResponse], summary="Listar todos los empleados")
def list_users(
    role: UserRole = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Lista empleados, con filtros opcionales por rol y estado."""
    query = db.query(User).filter(User.role != UserRole.PATIENT)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    return query.order_by(User.full_name).all()


@router.get("/professionals", response_model=List[UserSummary], summary="Listar profesionales de salud")
def list_professionals(
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    """Lista todos los empleados activos excepto pacientes (para selector de agenda)."""
    return db.query(User).filter(
        User.role != UserRole.PATIENT,
        User.is_active == True
    ).order_by(User.full_name).all()


@router.get("/by-document/{document_number}", response_model=UserResponse, summary="Buscar usuario por documento")
def get_user_by_document(
    document_number: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.document_number == document_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="No existe usuario con ese documento")
    return user


@router.get("/{user_id}", response_model=UserResponse, summary="Ver empleado por ID")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.patch("/{user_id}", response_model=UserResponse, summary="Actualizar empleado")
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Un admin puede editar cualquier usuario. Un empleado solo puede editar sus propios datos."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este usuario")

    # Solo admin puede desactivar usuarios o cambiar rol
    if body.is_active is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo el admin puede activar/desactivar usuarios")
    if body.role is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo el admin puede cambiar el rol")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", summary="Desactivar empleado")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Desactiva (no elimina) un empleado."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_active = False
    db.commit()
    return {"message": f"Usuario {user.full_name} desactivado correctamente"}
