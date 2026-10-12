"""Admin routers: settings, audit log, backups, analytics/dashboard."""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from lifeops.api.deps import get_db, require_not_stopped
from lifeops.api.helpers import paged, raise_lookup, raise_value
from lifeops.backup.manager import BackupManager
from lifeops.services import crud
from lifeops.services.settings_service import AUTONOMY_PROFILES, SettingsService
from lifeops.storage.models import (AgentRun, Approval, ApprovalDecision, AuditEvent,
                                    Notification, Task, TaskStatus)

router = APIRouter(prefix="/api/v1", tags=["admin"], dependencies=[Depends(require_not_stopped)])


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@router.get("/settings")
def get_settings(db: DBSession = Depends(get_db)):
    return SettingsService(db).get_all()


@router.get("/settings/{section}")
def get_settings_section(section: str, db: DBSession = Depends(get_db)):
    all_settings = SettingsService(db).get_all()
    if section not in all_settings:
        raise_lookup(LookupError(f"Unknown settings section '{section}'"))
    return {section: all_settings[section]}


@router.put("/settings/{section}")
def update_settings(section: str, payload: dict, db: DBSession = Depends(get_db)):
    updates = payload.get("updates", payload)
    confirm = bool(payload.get("confirm_exposure", False)) if "updates" in payload else False
    try:
        merged = SettingsService(db).update(section, updates, confirm_exposure=confirm)
    except ValueError as exc:
        raise_value(exc)
    return {"section": section, "values": merged}


@router.delete("/settings/{section}/reset")
def reset_settings(section: str, db: DBSession = Depends(get_db)):
    return {section: SettingsService(db).restore_defaults(section)}


@router.get("/settings/export/get")
def export_settings(db: DBSession = Depends(get_db)):
    import json
    return json.loads(SettingsService(db).export_settings())


@router.post("/settings/import")
def import_settings(payload: dict, db: DBSession = Depends(get_db)):
    results = SettingsService(db).import_settings(payload)
    return {"results": results}


@router.get("/settings/autonomy/profiles")
def autonomy_profiles(db: DBSession = Depends(get_db)):
    current = SettingsService(db).get_autonomy_profile()
    return {"current": current, "available": {k: v["description"] for k, v in AUTONOMY_PROFILES.items()}}


@router.post("/settings/autonomy/profile")
def set_autonomy_profile(payload: dict, db: DBSession = Depends(get_db)):
    profile = payload.get("profile", "")
    try:
        val = SettingsService(db).set_autonomy_profile(profile)
    except ValueError as exc:
        raise_value(exc)
    return val


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

@router.get("/audit/events")
def audit_events(actor: Optional[str] = None, action: Optional[str] = None,
                 outcome: Optional[str] = None, limit: int = 200,
                 db: DBSession = Depends(get_db)):
    q = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc())
    if actor:
        q = q.filter(AuditEvent.actor == actor)
    if action:
        q = q.filter(AuditEvent.action.like(f"{action}%"))
    if outcome:
        q = q.filter(AuditEvent.outcome == outcome)
    rows = q.limit(min(limit, 1000)).all()
    return [crud.to_dict(e) for e in rows]


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------

def _backup_manager(request: Request, db: DBSession) -> BackupManager:
    settings = SettingsService(db).get_section("storage")
    db_url = settings.get("database_url", "sqlite:///data/lifeops.db")
    db_path = db_url.replace("sqlite:///", "") if db_url.startswith("sqlite") else "data/lifeops.db"
    backup_dir = settings.get("backup_location", "data/backups")
    # Honour test overrides via app.state
    override = getattr(request.app.state, "db_path", None)
    if override:
        db_path = override
    return BackupManager(db, db_path=db_path, backup_dir=backup_dir)


@router.get("/backups")
def list_backups(request: Request, db: DBSession = Depends(get_db)):
    return _backup_manager(request, db).list_backups()


@router.post("/backups")
def create_backup(request: Request, payload: dict = None, db: DBSession = Depends(get_db)):
    payload = payload or {}
    try:
        result = _backup_manager(request, db).create_backup(
            description=payload.get("description", ""),
            include_files=payload.get("include_files"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"backup failed: {exc}")
    return result


@router.post("/backups/{backup_id}/verify")
def verify_backup(backup_id: str, request: Request, db: DBSession = Depends(get_db)):
    try:
        return _backup_manager(request, db).verify_backup(backup_id)
    except LookupError as exc:
        raise_lookup(exc)


@router.get("/backups/{backup_id}/preview-restore")
def preview_restore(backup_id: str, request: Request, db: DBSession = Depends(get_db)):
    try:
        return _backup_manager(request, db).preview_restore(backup_id)
    except LookupError as exc:
        raise_lookup(exc)


@router.post("/backups/{backup_id}/restore")
def restore_backup(backup_id: str, request: Request, payload: dict = None,
                   db: DBSession = Depends(get_db)):
    payload = payload or {}
    if not payload.get("confirm", False):
        raise HTTPException(status_code=422,
                            detail="restore requires confirm=true (destructive operation)")
    mgr = _backup_manager(request, db)
    try:
        result = mgr.restore(backup_id)
    except LookupError as exc:
        raise_lookup(exc)
    except ValueError as exc:
        raise_value(exc)
    from lifeops.security.policy import log_audit_event
    log_audit_event(db, actor="user", action="backup.restore", target=backup_id,
                    outcome="success", details=result)
    return result


@router.post("/backups/retention")
def apply_retention(request: Request, payload: dict = None, db: DBSession = Depends(get_db)):
    keep = int((payload or {}).get("keep", 10))
    removed = _backup_manager(request, db).apply_retention(keep=max(1, keep))
    return {"removed": removed, "keep": keep}


# ---------------------------------------------------------------------------
# Analytics / dashboard aggregate
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def dashboard(db: DBSession = Depends(get_db)):
    tasks_by_status = dict(db.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
    tasks_by_status = {(k.value if hasattr(k, "value") else str(k)): v for k, v in tasks_by_status.items()}
    pending_approvals = db.query(Approval).filter(Approval.decision == ApprovalDecision.PENDING).count()
    runs_total = db.query(AgentRun).count()
    runs_succeeded = db.query(AgentRun).filter(AgentRun.status == TaskStatus.SUCCEEDED).count()
    unread = db.query(Notification).filter(Notification.read == False).count()  # noqa: E712
    today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    activity_today = db.query(AuditEvent).filter(AuditEvent.timestamp >= today).count()
    overdue = db.query(Task).filter(Task.due_date < today,
                                    Task.status.notin_([TaskStatus.SUCCEEDED, TaskStatus.CANCELLED])).count()
    return {
        "tasks_by_status": tasks_by_status,
        "tasks_total": sum(tasks_by_status.values()),
        "pending_approvals": pending_approvals,
        "agent_runs": {"total": runs_total, "succeeded": runs_succeeded,
                        "success_rate": round(runs_succeeded / runs_total, 3) if runs_total else None},
        "unread_notifications": unread,
        "audit_events_today": activity_today,
        "overdue_tasks": overdue,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


@router.get("/analytics/summary")
def analytics(db: DBSession = Depends(get_db)):
    from lifeops.storage.models import Evaluation
    recent_evals = (db.query(Evaluation).order_by(Evaluation.created_at.desc()).limit(10).all())
    top_actions = (db.query(AuditEvent.action, func.count(AuditEvent.id))
                   .group_by(AuditEvent.action).order_by(func.count(AuditEvent.id).desc())
                   .limit(10).all())
    return {
        "recent_evaluations": [crud.to_dict(e) for e in recent_evals],
        "top_audit_actions": [{"action": a, "count": c} for a, c in top_actions],
    }
