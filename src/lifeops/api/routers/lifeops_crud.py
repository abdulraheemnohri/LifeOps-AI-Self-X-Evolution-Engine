"""LifeOps essentials: tasks, projects, calendar, notes, memory, documents, search, notifications."""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from lifeops.api.deps import get_db, require_not_stopped
from lifeops.api.helpers import paged, raise_lookup, raise_value
from lifeops.lifeops.tasks import DailyPlannerEngine, NotificationService, TaskService
from lifeops.security.policy import log_audit_event
from lifeops.selfx.engine import SelfMemory
from lifeops.services import crud
from lifeops.services.content import (CalendarService, DocumentService, NoteService,
                                      ProjectService, SearchService)
from lifeops.storage.models import (CalendarEvent, Document, Memory, Note, Notification,
                                    Project, Task, TaskStatus)

router = APIRouter(prefix="/api/v1", tags=["lifeops"], dependencies=[Depends(require_not_stopped)])


def _parse_dt(value) -> Optional[datetime.datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value
    return datetime.datetime.fromisoformat(str(value))


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@router.get("/tasks")
def list_tasks(status: Optional[str] = None, project_id: Optional[int] = None,
               page: int = 1, page_size: int = 50, paginated: bool = False,
               db: DBSession = Depends(get_db)):
    q = db.query(Task)
    if status:
        try:
            q = q.filter(Task.status == TaskStatus(status.upper()))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"invalid status '{status}'")
    if project_id:
        q = q.filter(Task.project_id == project_id)
    q = q.order_by(Task.created_at.desc())
    if paginated:
        result = crud.paginate(q, page, page_size)
        return paged(result, lambda t: crud.to_dict(t))
    return [crud.to_dict(t) for t in q.all()]


@router.post("/tasks")
def create_task(payload: dict, db: DBSession = Depends(get_db)):
    svc = TaskService(db)
    task = svc.create_task(
        title=payload.get("title", "Untitled Task"),
        description=payload.get("description"),
        priority=payload.get("priority", "medium"),
        due_date=_parse_dt(payload.get("due_date")),
        category=payload.get("category"),
        tags=payload.get("tags") or [],
        project_id=payload.get("project_id"),
    )
    log_audit_event(db, actor="user", action="task.create", target=f"Task:{task.id}", outcome="success")
    return crud.to_dict(task)


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: DBSession = Depends(get_db)):
    try:
        return crud.to_dict(crud.get_or_404(db, Task, task_id))
    except LookupError as exc:
        raise_lookup(exc)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: dict, db: DBSession = Depends(get_db)):
    task = crud.get_or_404(db, Task, task_id)
    data = dict(payload)
    if "due_date" in data:
        data["due_date"] = _parse_dt(data["due_date"])
    if "status" in data:
        data["status"] = TaskStatus(data["status"].upper())
    allowed = {k: v for k, v in data.items()
               if k in ("title", "description", "priority", "status", "due_date",
                        "category", "tags", "project_id", "completion_notes")}
    try:
        task = crud.apply_update(db, task, allowed, action="task.update")
    except ValueError as exc:
        raise_value(exc)
    return crud.to_dict(task)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: DBSession = Depends(get_db)):
    task = crud.get_or_404(db, Task, task_id)
    crud.delete_object(db, task, action="task.delete")
    return {"status": "deleted", "id": task_id}


@router.post("/tasks/{task_id}/transition")
def transition_task(task_id: int, payload: dict, db: DBSession = Depends(get_db)):
    svc = TaskService(db)
    try:
        new_status = TaskStatus(payload.get("status", "").upper())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"invalid status '{payload.get('status')}'")
    task = svc.update_task_status(task_id, new_status, payload.get("completion_notes"))
    if not task:
        raise_lookup(LookupError(f"Task '{task_id}' not found"))
    log_audit_event(db, actor="user", action="task.transition",
                    target=f"Task:{task_id}", outcome="success", details={"status": new_status.value})
    return crud.to_dict(task)


@router.get("/tasks/actions/daily-plan")
def daily_plan(date: Optional[str] = None, db: DBSession = Depends(get_db)):
    d = datetime.date.fromisoformat(date) if date else None
    return DailyPlannerEngine(db).generate_daily_plan(d)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@router.get("/projects")
def list_projects(page: int = 1, page_size: int = 50, db: DBSession = Depends(get_db)):
    result = crud.paginate(db.query(Project).order_by(Project.id), page, page_size)
    return paged(result, lambda p: crud.to_dict(p))


@router.post("/projects")
def create_project(payload: dict, db: DBSession = Depends(get_db)):
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="project name is required")
    p = ProjectService(db).create(name=name, description=payload.get("description"))
    return crud.to_dict(p)


@router.patch("/projects/{project_id}")
def update_project(project_id: int, payload: dict, db: DBSession = Depends(get_db)):
    try:
        proj = crud.get_or_404(db, Project, project_id)
        allowed = {k: v for k, v in payload.items() if k in ("name", "description", "status")}
        return crud.to_dict(crud.apply_update(db, proj, allowed, action="project.update"))
    except LookupError as exc:
        raise_lookup(exc)


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: DBSession = Depends(get_db)):
    proj = crud.get_or_404(db, Project, project_id)
    crud.delete_object(db, proj, action="project.delete")
    return {"status": "deleted", "id": project_id}


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

@router.get("/calendar/events")
def list_events(start: Optional[str] = None, end: Optional[str] = None,
                page: int = 1, page_size: int = 50, db: DBSession = Depends(get_db)):
    svc = CalendarService(db)
    if start and end:
        events = svc.events_for_range(_parse_dt(start), _parse_dt(end))
        return {"items": [crud.to_dict(e) for e in events], "total": len(events),
                "page": 1, "page_size": len(events)}
    result = crud.paginate(db.query(CalendarEvent).order_by(CalendarEvent.start_time), page, page_size)
    return paged(result, lambda e: crud.to_dict(e))


@router.post("/calendar/events")
def create_event(payload: dict, db: DBSession = Depends(get_db)):
    svc = CalendarService(db)
    try:
        ev = svc.create_event(
            title=payload.get("title", "Untitled Event"),
            start_time=_parse_dt(payload.get("start_time")),
            end_time=_parse_dt(payload.get("end_time")),
            description=payload.get("description"),
            time_zone=payload.get("time_zone", "UTC"),
            recurrence_rule=payload.get("recurrence_rule"),
        )
    except (ValueError, TypeError) as exc:
        raise_value(ValueError(str(exc)))
    return crud.to_dict(ev)


@router.get("/calendar/events/{event_id}/conflicts")
def event_conflicts(event_id: int, db: DBSession = Depends(get_db)):
    return {"event_id": event_id, "conflicts": CalendarService(db).find_conflicts(event_id)}


@router.patch("/calendar/events/{event_id}")
def update_event(event_id: int, payload: dict, db: DBSession = Depends(get_db)):
    ev = crud.get_or_404(db, CalendarEvent, event_id)
    data = {k: v for k, v in payload.items()
            if k in ("title", "description", "time_zone", "recurrence_rule", "is_recurring")}
    if "start_time" in payload:
        data["start_time"] = _parse_dt(payload["start_time"])
    if "end_time" in payload:
        data["end_time"] = _parse_dt(payload["end_time"])
    if "start_time" in data and "end_time" in data and data["end_time"] <= data["start_time"]:
        raise_value(ValueError("end_time must be after start_time"))
    return crud.to_dict(crud.apply_update(db, ev, data, action="calendar.update"))


@router.delete("/calendar/events/{event_id}")
def delete_event(event_id: int, db: DBSession = Depends(get_db)):
    ev = crud.get_or_404(db, CalendarEvent, event_id)
    crud.delete_object(db, ev, action="calendar.delete")
    return {"status": "deleted", "id": event_id}


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@router.get("/notes")
def list_notes(query: Optional[str] = None, page: int = 1, page_size: int = 50,
               db: DBSession = Depends(get_db)):
    svc = NoteService(db)
    if query:
        notes = svc.search_notes(query)
        return {"items": [crud.to_dict(n) for n in notes], "total": len(notes),
                "page": 1, "page_size": len(notes)}
    result = crud.paginate(db.query(Note).order_by(Note.updated_at.desc()), page, page_size)
    return paged(result, lambda n: crud.to_dict(n))


@router.post("/notes")
def create_note(payload: dict, db: DBSession = Depends(get_db)):
    title = payload.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="note title is required")
    note = NoteService(db).create_note(title=title, content=payload.get("content", ""),
                                       tags=payload.get("tags") or [])
    return crud.to_dict(note)


@router.get("/notes/graph")
def notes_graph(db: DBSession = Depends(get_db)):
    return NoteService(db).graph()


@router.get("/notes/{note_id}")
def get_note(note_id: int, db: DBSession = Depends(get_db)):
    try:
        return crud.to_dict(crud.get_or_404(db, Note, note_id))
    except LookupError as exc:
        raise_lookup(exc)


@router.patch("/notes/{note_id}")
def update_note(note_id: int, payload: dict, db: DBSession = Depends(get_db)):
    note = NoteService(db).update_note(note_id, payload)
    if not note:
        raise_lookup(LookupError(f"Note '{note_id}' not found"))
    return crud.to_dict(note)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: DBSession = Depends(get_db)):
    note = crud.get_or_404(db, Note, note_id)
    crud.delete_object(db, note, action="note.delete")
    return {"status": "deleted", "id": note_id}


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@router.get("/memory")
def list_memories(category: Optional[str] = None, query: Optional[str] = None,
                  page: int = 1, page_size: int = 50, db: DBSession = Depends(get_db)):
    mems = SelfMemory(db).retrieve_memories(category)
    items = [m for m in mems if not query or query.lower() in (m.key or "").lower()
             or query.lower() in (m.value or "").lower()]
    start_idx = (max(1, page) - 1) * page_size
    window = items[start_idx:start_idx + page_size]
    return {"items": [crud.to_dict(m) for m in window], "total": len(items),
            "page": page, "page_size": page_size}


@router.post("/memory")
def store_memory(payload: dict, db: DBSession = Depends(get_db)):
    for field in ("category", "key", "value"):
        if not payload.get(field):
            raise HTTPException(status_code=422, detail=f"'{field}' is required")
    mem = SelfMemory(db).store_memory(payload["category"], payload["key"], payload["value"],
                                      provenance=payload.get("provenance", "manual"))
    log_audit_event(db, actor="user", action="memory.store",
                    target=f"Memory:{mem.id}", outcome="success")
    return crud.to_dict(mem)


@router.get("/memory/{memory_id}/revisions")
def memory_revisions(memory_id: int, db: DBSession = Depends(get_db)):
    from lifeops.storage.models import MemoryRevision
    crud.get_or_404(db, Memory, memory_id)
    rows = db.query(MemoryRevision).filter_by(memory_id=memory_id).all()
    return {"memory_id": memory_id, "revisions": [crud.to_dict(r) for r in rows]}


@router.patch("/memory/{memory_id}")
def update_memory(memory_id: int, payload: dict, db: DBSession = Depends(get_db)):
    mem = crud.get_or_404(db, Memory, memory_id)
    old_value = mem.value
    data = {k: v for k, v in payload.items() if k in ("category", "key", "value", "confidence", "is_stale")}
    mem = crud.apply_update(db, mem, data, action="memory.update")
    if "value" in data and data["value"] != old_value:
        db.add(MemoryRevisionX(mem.id, old_value, data["value"]))
        db.commit()
    return crud.to_dict(mem)


def MemoryRevisionX(memory_id, old_value, new_value):
    from lifeops.storage.models import MemoryRevision
    return MemoryRevision(memory_id=memory_id, old_value=old_value, new_value=new_value)


@router.delete("/memory/{memory_id}")
def delete_memory(memory_id: int, db: DBSession = Depends(get_db)):
    mem = crud.get_or_404(db, Memory, memory_id)
    crud.delete_object(db, mem, action="memory.delete")
    return {"status": "deleted", "id": memory_id}


@router.post("/memory/export")
def export_memory(db: DBSession = Depends(get_db)):
    mems = SelfMemory(db).retrieve_memories()
    return {"exported": [crud.to_dict(m) for m in mems], "count": len(mems)}


# ---------------------------------------------------------------------------
# Documents / files
# ---------------------------------------------------------------------------

@router.get("/documents")
def list_documents(page: int = 1, page_size: int = 50, db: DBSession = Depends(get_db)):
    result = crud.paginate(db.query(Document).order_by(Document.filename), page, page_size)
    return paged(result, lambda d: crud.to_dict(d))


@router.post("/documents/index")
def index_directory(payload: dict, db: DBSession = Depends(get_db)):
    directory = payload.get("directory", "")
    if not directory:
        raise HTTPException(status_code=422, detail="'directory' is required")
    try:
        stats = DocumentService(db).index_directory(directory)
    except ValueError as exc:
        raise_value(exc)
    log_audit_event(db, actor="user", action="documents.index", target=directory,
                    outcome="success", details=stats)
    return stats


@router.get("/documents/search")
def search_documents(q: str = Query(..., min_length=1), db: DBSession = Depends(get_db)):
    return {"query": q, "results": DocumentService(db).search_documents(q)}


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: DBSession = Depends(get_db)):
    doc = crud.get_or_404(db, Document, document_id)
    crud.delete_object(db, doc, action="documents.delete")
    return {"status": "deleted", "id": document_id}


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------

@router.get("/search")
def unified_search(q: str = Query(..., min_length=1), db: DBSession = Depends(get_db)):
    return SearchService(db).search(q)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications")
def list_notifications(unread_only: bool = False, page: int = 1, page_size: int = 50,
                       db: DBSession = Depends(get_db)):
    q = db.query(Notification).order_by(Notification.created_at.desc())
    if unread_only:
        q = q.filter(Notification.read == False)  # noqa: E712
    result = crud.paginate(q, page, page_size)
    return paged(result, lambda n: crud.to_dict(n))


@router.post("/notifications")
def create_notification(payload: dict, db: DBSession = Depends(get_db)):
    notif = NotificationService(db).send_notification(
        title=payload.get("title", "Notice"),
        message=payload.get("message", ""),
        level=payload.get("level", "info"),
    )
    return crud.to_dict(notif)


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, db: DBSession = Depends(get_db)):
    notif = crud.get_or_404(db, Notification, notification_id)
    notif.read = True
    db.commit()
    return crud.to_dict(notif)
