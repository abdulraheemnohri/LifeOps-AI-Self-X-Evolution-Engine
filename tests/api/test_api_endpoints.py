import pytest
from fastapi.testclient import TestClient
from lifeops.storage.database import get_engine, init_db, get_session_factory
from lifeops.storage.models import User
from lifeops.security.auth import hash_password, create_session
from lifeops.api.router import app
from lifeops.api.deps import set_test_session_factory

def test_api_endpoints(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = get_session_factory(engine)
    set_test_session_factory(session_factory)

    db = session_factory()
    try:
        user = User(username="admin", password_hash=hash_password("adminpassword123").encoded, role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        sess = create_session(db, user.id)
        raw_token = getattr(sess, "_raw_token", sess.id)
    finally:
        db.close()

    client = TestClient(app)
    client.cookies.set("lifeops_session", raw_token)

    # Health check
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # Identity check
    res = client.get("/api/v1/system/identity")
    assert res.status_code == 200
    assert res.json()["app_name"] == "LifeOps AI + Self-X Evolution Engine"

    # Tasks API
    res = client.post("/api/v1/tasks", json={"title": "API Task Test", "priority": "high"})
    assert res.status_code == 200
    task_data = res.json()
    assert task_data["title"] == "API Task Test"

    res = client.get("/api/v1/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "API Task Test"
