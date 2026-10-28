from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models import AuditLog


def log_action(
    db: Session,
    actor: str,
    action: str,
    entity: str,
    details: Optional[Any] = None,
) -> AuditLog:
    """Log an action to the audit_logs table and persist it."""
    payload = details if isinstance(details, (dict, list)) else ({"value": details} if details is not None else None)
    audit_entry = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        details=payload,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
