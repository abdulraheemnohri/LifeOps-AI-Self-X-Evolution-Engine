"""LifeOps content services: projects, calendar, notes, documents, search."""
import datetime
import hashlib
import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from lifeops.storage.models import (
    Project, CalendarEvent, Note, Document, DocumentChunk, Task,
)


class ProjectService:
    def __init__(self, db: DBSession):
        self.db = db

    def create(self, name: str, description: Optional[str] = None) -> Project:
        p = Project(name=name, description=description)
        self.db.add(p); self.db.commit(); self.db.refresh(p)
        return p


class CalendarService:
    def __init__(self, db: DBSession):
        self.db = db

    def create_event(self, title: str, start_time: datetime.datetime,
                     end_time: datetime.datetime, description: Optional[str] = None,
                     time_zone: str = "UTC", recurrence_rule: Optional[str] = None) -> CalendarEvent:
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        ev = CalendarEvent(title=title, start_time=start_time, end_time=end_time,
                           description=description, time_zone=time_zone,
                           recurrence_rule=recurrence_rule,
                           is_recurring=bool(recurrence_rule))
        self.db.add(ev); self.db.commit(); self.db.refresh(ev)
        return ev

    def events_for_range(self, start: datetime.datetime, end: datetime.datetime) -> List[CalendarEvent]:
        return (self.db.query(CalendarEvent)
                .filter(CalendarEvent.start_time >= start, CalendarEvent.start_time <= end)
                .order_by(CalendarEvent.start_time).all())

    def find_conflicts(self, event_id: int) -> List[Dict[str, Any]]:
        ev = self.db.get(CalendarEvent, event_id)
        if not ev:
            return []
        overlapping = (self.db.query(CalendarEvent)
                       .filter(CalendarEvent.id != ev.id,
                               CalendarEvent.start_time < ev.end_time,
                               CalendarEvent.end_time > ev.start_time).all())
        return [{"id": o.id, "title": o.title} for o in overlapping]


_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


class NoteService:
    def __init__(self, db: DBSession):
        self.db = db

    def create_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> Note:
        note = Note(title=title, content=content, tags=tags or [],
                    backlinks=self._extract_backlinks(content))
        self.db.add(note); self.db.commit(); self.db.refresh(note)
        return note

    def update_note(self, note_id: int, data: Dict[str, Any]) -> Optional[Note]:
        note = self.db.get(Note, note_id)
        if not note:
            return None
        for field in ("title", "content", "tags"):
            if field in data:
                setattr(note, field, data[field])
        if "content" in data:
            note.backlinks = self._extract_backlinks(data["content"])
        note.updated_at = datetime.datetime.utcnow()
        self.db.commit(); self.db.refresh(note)
        return note

    @staticmethod
    def _extract_backlinks(content: str) -> List[str]:
        return _WIKILINK_RE.findall(content or "")

    def search_notes(self, query: str) -> List[Note]:
        q = f"%{query.lower()}%"
        notes = self.db.query(Note).all()
        return [n for n in notes
                if query.lower() in (n.title or "").lower()
                or query.lower() in (n.content or "").lower()]

    def graph(self) -> Dict[str, Any]:
        """Backlink graph of all notes for the knowledge view."""
        notes = self.db.query(Note).all()
        nodes = [{"id": n.id, "title": n.title} for n in notes]
        edges = []
        titles = {n.title for n in notes}
        for n in notes:
            for bl in (n.backlinks or []):
                if bl in titles:
                    edges.append({"from": n.id, "to_title": bl})
        return {"nodes": nodes, "edges": edges}


class DocumentService:
    """Index local files into documents + chunks with hash-based dedupe."""

    ALLOWED_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".json", ".py"}

    def __init__(self, db: DBSession, workspace_dir: str = "workspace"):
        self.db = db
        self.workspace_dir = workspace_dir

    def index_directory(self, directory: str) -> Dict[str, Any]:
        # Path traversal guard: only index inside an explicitly existing dir.
        directory = os.path.realpath(directory)
        if not os.path.isdir(directory):
            raise ValueError("directory does not exist")
        indexed, skipped, errors = 0, 0, []
        for root, _dirs, files in os.walk(directory):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.ALLOWED_EXTENSIONS:
                    skipped += 1
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "rb") as fh:
                        raw = fh.read()
                except Exception as exc:
                    errors.append(f"{fpath}: {exc}")
                    continue
                file_hash = hashlib.sha256(raw).hexdigest()
                existing = self.db.query(Document).filter_by(filepath=fpath).first()
                if existing and existing.file_hash == file_hash:
                    skipped += 1
                    continue
                status = "indexed"
                doc = existing or Document(filepath=fpath, filename=fname)
                doc.file_hash = file_hash
                doc.file_size = len(raw)
                doc.mime_type = "text/plain"
                doc.last_modified = datetime.datetime.utcfromtimestamp(os.path.getmtime(fpath))
                doc.indexing_status = status
                doc.indexed_at = datetime.datetime.utcnow()
                if not existing:
                    self.db.add(doc)
                self.db.flush()
                # Replace chunks
                self.db.query(DocumentChunk).filter_by(document_id=doc.id).delete()
                text = raw.decode("utf-8", errors="replace")
                for i, chunk in enumerate(self._chunk(text)):
                    self.db.add(DocumentChunk(document_id=doc.id, chunk_index=i, content=chunk))
                indexed += 1
        self.db.commit()
        return {"indexed": indexed, "skipped": skipped, "errors": errors}

    @staticmethod
    def _chunk(text: str, size: int = 2000) -> List[str]:
        return [text[i:i + size] for i in range(0, len(text), size)] or [""]

    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        like = f"%{query}%"
        rows = (self.db.query(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .filter(DocumentChunk.content.like(like)).limit(50).all())
        return [{"document_id": d.id, "filename": d.filename,
                 "chunk_index": c.chunk_index, "excerpt": c.content[:300]}
                for c, d in rows]


class SearchService:
    """Unified local full-text-ish search across notes, memories, documents, tasks."""

    def __init__(self, db: DBSession):
        self.db = db

    def search(self, query: str) -> Dict[str, Any]:
        ql = query.lower()
        from lifeops.storage.models import Memory
        notes = self.db.query(Note).all()
        mems = self.db.query(Memory).all()
        docs = self.db.query(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id).all()
        tasks = self.db.query(Task).all()
        return {
            "query": query,
            "notes": [{"id": n.id, "title": n.title} for n in notes
                      if ql in (n.title or "").lower() or ql in (n.content or "").lower()],
            "memories": [{"id": m.id, "key": m.key, "category": m.category} for m in mems
                         if ql in (m.key or "").lower() or ql in (m.value or "").lower()],
            "documents": [{"document_id": d.id, "filename": d.filename, "chunk_index": c.chunk_index}
                          for c, d in docs if ql in (c.content or "").lower()],
            "tasks": [{"id": t.id, "title": t.title} for t in tasks if ql in (t.title or "").lower()],
        }
