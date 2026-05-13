from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, UserRole
from models.patient import Patient, DocumentType, Gender
from schemas.auth import TokenResponse, LoginRequest, PasswordChangeRequest, PatientRegisterRequest, StaffProfileUpdate
from core.security import verify_password, create_access_token, hash_password
from core.dependencies import get_current_user
from services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login con email y contraseña.
    Retorna un token JWT válido por 8 horas.
    """
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador.",
        )

    token = create_access_token(data={"sub": str(user.id)})
    log_action(db, "inicio_sesion", "sesion", f"{user.full_name} inició sesión", user=user, entity_id=user.id)
    db.commit()
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
    )


@router.post("/login/json", response_model=TokenResponse, summary="Iniciar sesión (JSON)")
def login_json(body: LoginRequest, db: Session = Depends(get_db)):
    """Versión JSON del login (alternativa a form-data)."""
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador.",
        )

    token = create_access_token(data={"sub": str(user.id)})
    log_action(db, "inicio_sesion", "sesion", f"{user.full_name} inició sesión", user=user, entity_id=user.id)
    db.commit()
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
    )


@router.get("/me", summary="Información del usuario actual")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna los datos del usuario autenticado."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "specialty": current_user.specialty,
    }


@router.post("/register", response_model=TokenResponse, status_code=201,
             summary="Registro de paciente (público)")
def register_patient(body: PatientRegisterRequest, db: Session = Depends(get_db)):
    """
    Permite que un paciente se registre sin intervención del personal.
    Crea un User con rol 'paciente' y un registro Patient vinculado.
    """
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo electrónico")
    if db.query(User).filter(User.document_number == body.document_number).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese número de documento")
    if db.query(Patient).filter(Patient.document_number == body.document_number).first():
        raise HTTPException(status_code=409, detail="Ya existe un paciente registrado con ese documento")

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    first_name, *rest = body.full_name.strip().split(" ", 1)
    last_name = rest[0] if rest else "—"

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        document_number=body.document_number,
        phone=body.phone,
        role=UserRole.PATIENT,
        is_active=True,
    )
    db.add(user)
    db.flush()  # obtener user.id antes del commit

    patient = Patient(
        document_type=body.document_type,
        document_number=body.document_number,
        first_name=first_name,
        last_name=last_name,
        birth_date=date.fromisoformat(body.birth_date),
        gender=body.gender,
        blood_type=body.blood_type,
        phone=body.phone,
        email=body.email,
        address=body.address,
        city=body.city,
        eps=body.eps,
        regime=body.regime,
        user_id=user.id,
    )
    db.add(patient)
    log_action(db, "registro", "usuario", f"Paciente {body.full_name} se registró en la plataforma", user=user, entity_id=user.id)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, full_name=user.full_name, role=user.role)


@router.patch("/profile", summary="Actualizar perfil propio (empleado)")
def update_profile(
    body: StaffProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name.strip()
    if body.phone is not None:
        current_user.phone = body.phone.strip() or None
    if body.email is not None:
        if body.email != current_user.email:
            if db.query(User).filter(User.email == body.email, User.id != current_user.id).first():
                raise HTTPException(status_code=409, detail="Ese correo ya está en uso")
        current_user.email = body.email
    log_action(db, "actualizar", "usuario", f"{current_user.full_name} actualizó su perfil", user=current_user, entity_id=current_user.id)
    db.commit()
    return {"message": "Perfil actualizado correctamente"}


@router.post("/change-password", summary="Cambiar contraseña")
def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permite al usuario cambiar su propia contraseña."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres")

    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Contraseña actualizada correctamente"}
