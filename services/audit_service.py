from sqlalchemy.orm import Session
from models.audit_log import AuditLog
from models.user import User


def log_action(
    db: Session,
    action: str,
    entity_type: str,
    description: str,
    user: User | None = None,
    entity_id: int | None = None,
) -> None:
    """Agrega un registro de auditoría a la sesión activa. El caller debe hacer commit."""
    entry = AuditLog(
        user_id=user.id if user else None,
        user_name=user.full_name if user else "Sistema",
        user_role=user.role.value if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(entry)
