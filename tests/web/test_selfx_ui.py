from starlette.testclient import TestClient
from lifeops.app import app, validate_bind_host
from lifeops.storage.models import User
from lifeops.security.auth import hash_password, create_session
from lifeops.database import get_session_factory, init_db

def _auth_client():
    engine = init_db()
    db = get_session_factory()()
    try:
        user = db.query(User).filter_by(username="ui_test_admin").first()
        if not user:
            user = User(username="ui_test_admin", password_hash=hash_password("adminpassword123").encoded, role="admin")
            db.add(user)
            db.commit()
            db.refresh(user)
        session_obj = create_session(db, user.id)
        token = getattr(session_obj, "_raw_token", session_obj.id)
    finally:
        db.close()
    client = TestClient(app)
    client.cookies.set("lifeops_session", token)
    client.cookies.set("lifeops_csrf", "test_csrf_token")
    return client

def test_health_reports_model_unavailable_without_claiming_execution():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_runtime"] == "not_configured"

def test_selfx_ui_exposes_goal_proposal_and_evidence_sections():
    client = _auth_client()
    response = client.get("/selfx")
    assert response.status_code == 200
    assert "Improvement goal" in response.text
    assert "Improvement proposal" in response.text
    assert "Evaluation history" in response.text

def test_selfx_rejects_empty_goal():
    client = _auth_client()
    response = client.post("/selfx/goals", data={"title": "", "objective": "", "_csrf": "test_csrf_token"})
    assert response.status_code == 200
    assert "Goal title and objective are required" in response.text

def test_remote_binding_is_always_rejected_until_security_controls_exist():
    import pytest
    with pytest.raises(ValueError, match="Remote binding is disabled"):
        validate_bind_host("0.0.0.0")
    assert validate_bind_host("127.0.0.1") == "127.0.0.1"
