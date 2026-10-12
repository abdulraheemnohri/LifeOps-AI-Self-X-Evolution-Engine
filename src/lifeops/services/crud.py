"""Generic CRUD helpers shared by the API and the Web UI.

Business logic lives in services (never duplicated in browser code). These
helpers provide pagination, validation-driven updates, and audit logging.
"""
import datetime
import enum
from typing import Any, Dict, List, Optional, Type

from sqlalchemy.orm import Session as DBSession

from lifeops.storage.models import Base
from lifeops.security.policy import log_audit_event


def paginate(query, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_or_404(db: DBSession, model: Type[Base], item_id: Any):
    obj = db.get(model, item_id)
    if obj is None:
        raise LookupError(f"{model.__name__} '{item_id}' not found")
    return obj


def apply_update(db: DBSession, obj: Base, data: Dict[str, Any], actor: str = "user",
                 action: Optional[str] = None) -> Base:
    """Apply a validated partial update dict to an ORM object."""
    for field, value in data.items():
        if hasattr(obj, field) and field not in ("id", "created_at"):
            setattr(obj, field, value)
    if hasattr(obj, "updated_at"):
        obj.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(obj)
    if action:
        log_audit_event(db, actor=actor, action=action,
                        target=f"{type(obj).__name__}:{getattr(obj, 'id', '?')}",
                        outcome="success", details={"fields": sorted(data.keys())})
    return obj


def delete_object(db: DBSession, obj: Base, actor: str = "user", action: Optional[str] = None):
    db.delete(obj)
    db.commit()
    if action:
        log_audit_event(db, actor=actor, action=action,
                        target=f"{type(obj).__name__}", outcome="success")


def to_dict(obj: Base, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    exclude = set(exclude or [])
    out: Dict[str, Any] = {}
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(obj, col.name)
        if isinstance(val, enum.Enum):
            val = val.value
        elif isinstance(val, (datetime.datetime, datetime.date)):
            val = val.isoformat()
        out[col.name] = val
    return out
