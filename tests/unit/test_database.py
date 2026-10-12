import os
import pytest
from sqlalchemy import inspect
from lifeops.storage.database import get_engine, init_db, get_session_factory
from lifeops.storage.models import Base, User, Task, TaskStatus

def test_init_db_and_tables(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = get_engine(db_url)
    init_db(engine)

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    assert "users" in table_names
    assert "tasks" in table_names
    assert "settings" in table_names
    assert "agent_runs" in table_names
    assert "skills" in table_names
    assert "selfx_goals" in table_names
    assert "audit_events" in table_names
    assert len(table_names) >= 33

def test_user_and_task_creation(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = get_engine(db_url)
    init_db(engine)
    SessionFactory = get_session_factory(engine)

    session = SessionFactory()
    user = User(username="admin", password_hash="hashed_pw")
    session.add(user)
    session.commit()

    fetched_user = session.query(User).filter_by(username="admin").first()
    assert fetched_user is not None
    assert fetched_user.id == 1

    task = Task(title="Test Task", priority="high", status=TaskStatus.CREATED)
    session.add(task)
    session.commit()

    fetched_task = session.query(Task).filter_by(title="Test Task").first()
    assert fetched_task is not None
    assert fetched_task.status == TaskStatus.CREATED
    session.close()
