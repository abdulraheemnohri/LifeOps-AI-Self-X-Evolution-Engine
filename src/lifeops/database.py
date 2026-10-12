"""SQLite persistence and SQLAlchemy models for the local-first foundation."""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def database_url() -> str:
    configured = os.getenv("LIFEOPS_DATABASE_URL")
    if configured: return configured
    data_dir = Path(os.getenv("LIFEOPS_DATA_DIR", "data")).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'lifeops.db').as_posix()}"

class Base(DeclarativeBase): pass

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    priority: Mapped[str] = mapped_column(String(12), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

_engine = None
_SessionLocal = None

def configure_database(url: str | None = None):
    global _engine, _SessionLocal
    if _engine is not None: _engine.dispose()
    target = url or database_url()
    kwargs = {"check_same_thread": False} if target.startswith("sqlite") else {}
    _engine = create_engine(target, connect_args=kwargs, future=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine

def get_session_factory():
    global _engine, _SessionLocal
    if _SessionLocal is None: configure_database()
    return _SessionLocal

def init_db():
    global _engine
    if _engine is None: configure_database()
    Base.metadata.create_all(bind=_engine)
    return _engine

configure_database()
