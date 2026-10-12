"""FastAPI test fixtures: isolated temp SQLite DB per test, TestClient factory."""
import pytest
from fastapi.testclient import TestClient

from lifeops.api.deps import set_test_session_factory, emergency_stop
from lifeops.api.router import app
from lifeops.storage.database import get_engine, get_session_factory, init_db
from lifeops.storage.models import User
from lifeops.security.auth import hash_password, create_session
from lifeops.scheduler.worker import WorkerQueue, Scheduler


@pytest.fixture()
def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    factory = get_session_factory(engine)
    set_test_session_factory(factory)
    # Keep process-wide emergency stop from leaking between tests.
    emergency_stop.release()
    yield factory
    set_test_session_factory(None)
    emergency_stop.release()


@pytest.fixture()
def client(session_factory):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(session_factory):
    db = session_factory()
    try:
        user = User(username="admin", password_hash=hash_password("adminpassword123").encoded, role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        session_obj = create_session(db, user.id)
        token = getattr(session_obj, "_raw_token", session_obj.id)
    finally:
        db.close()

    # Set up mock worker queue & scheduler on app state if not present
    if not hasattr(app.state, "worker_queue") or app.state.worker_queue is None:
        queue = WorkerQueue(session_factory)
        app.state.worker_queue = queue
        app.state.scheduler = Scheduler(session_factory, queue)

    with TestClient(app) as c:
        c.cookies.set("lifeops_session", token)
        yield c


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
