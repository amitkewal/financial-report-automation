from sqlalchemy.orm import Session

from app import models


def log(db: Session, entity_type: str, entity_id: int | None, actor_id: int | None, action: str, details: str = ""):
    db.add(
        models.AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            action=action,
            details=details,
        )
    )
    db.commit()
