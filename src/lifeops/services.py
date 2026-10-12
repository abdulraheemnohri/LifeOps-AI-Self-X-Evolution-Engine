"""Validated business services shared by browser routes and background workers."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import Task, Note, AuditEvent
VALID_PRIORITIES = {"low", "medium", "high"}
class ValidationError(ValueError): pass

def _audit(db: Session, event_type: str, details: str) -> None:
    db.add(AuditEvent(event_type=event_type, details=details[:1000]))

def create_task(db: Session, title: str, description: str = "", priority: str = "medium") -> Task:
    title = title.strip()
    if not title or len(title) > 240: raise ValidationError("Task title must contain 1–240 characters.")
    if priority not in VALID_PRIORITIES: raise ValidationError("Priority must be low, medium, or high.")
    task = Task(title=title, description=description.strip()[:10000], priority=priority)
    db.add(task); _audit(db, "task.created", f"title={title}"); db.commit(); db.refresh(task)
    return task

def list_tasks(db: Session, status: str | None = None) -> list[Task]:
    stmt = select(Task).order_by(Task.created_at.desc(), Task.id.desc())
    if status in {"open", "completed"}: stmt = stmt.where(Task.status == status)
    return list(db.scalars(stmt).all())

def complete_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None: raise LookupError("Task not found.")
    task.status = "completed"; task.completed_at = datetime.now(timezone.utc)
    _audit(db, "task.completed", f"task_id={task.id}"); db.commit(); db.refresh(task)
    return task

def create_note(db: Session, title: str, content: str = "") -> Note:
    title = title.strip()
    if not title or len(title) > 240: raise ValidationError("Note title must contain 1–240 characters.")
    if len(content) > 100000: raise ValidationError("Note content exceeds 100,000 characters.")
    note = Note(title=title, content=content); db.add(note); _audit(db, "note.created", f"title={title}")
    db.commit(); db.refresh(note); return note

def list_notes(db: Session) -> list[Note]:
    return list(db.scalars(select(Note).order_by(Note.updated_at.desc(), Note.id.desc())).all())
