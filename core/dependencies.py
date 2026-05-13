from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from core.security import decode_access_token
from models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extrae y valida el usuario del token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: UserRole):
    """Factory de dependencia que verifica que el usuario tenga uno de los roles permitidos."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Roles permitidos: {[r.value for r in roles]}",
            )
        return current_user
    return role_checker


# Atajos de dependencia por rol
require_admin = require_roles(UserRole.ADMIN)
require_admin_or_receptionist = require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST)
require_medical_staff = require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE)
require_any_staff = require_roles(
    UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.AUDITOR
)
require_patient = require_roles(UserRole.PATIENT)
require_any_authenticated = require_roles(
    UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE,
    UserRole.RECEPTIONIST, UserRole.AUDITOR, UserRole.PATIENT
)
