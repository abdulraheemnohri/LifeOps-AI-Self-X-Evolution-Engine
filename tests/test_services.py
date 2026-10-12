from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import pytest
from lifeops.database import Base, Task, AuditEvent
from lifeops.services import create_task, list_tasks, complete_task, create_note, list_notes, ValidationError

@pytest.fixture
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session: yield session
    engine.dispose()

def test_create_and_list_task(db):
    task=create_task(db,"  Ship phase one  ","first milestone","high")
    assert task.title=="Ship phase one" and task.status=="open"
    assert list_tasks(db)[0].id==task.id

def test_task_validation(db):
    with pytest.raises(ValidationError): create_task(db,"  ")
    with pytest.raises(ValidationError): create_task(db,"valid",priority="urgent")

def test_complete_task_is_persisted_and_audited(db):
    task=create_task(db,"Test completion"); complete_task(db,task.id)
    assert db.get(Task,task.id).status=="completed"
    assert db.scalars(select(AuditEvent).where(AuditEvent.event_type=="task.completed")).first()

def test_complete_missing_task(db):
    with pytest.raises(LookupError): complete_task(db,999)

def test_notes_round_trip(db):
    note=create_note(db," Useful note ","body")
    assert note.title=="Useful note" and list_notes(db)[0].content=="body"
    with pytest.raises(ValidationError): create_note(db,"")
