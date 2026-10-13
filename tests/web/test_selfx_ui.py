from starlette.testclient import TestClient
from lifeops.app import app as fasthtml_app, validate_bind_host

def _login(client):
    res = client.post("/login", data={"username": "admin", "password": "adminpassword123"})
    if "Invalid" in res.text or "Sign in" in res.text:
        client.post("/setup", data={"username": "admin", "password": "adminpassword123", "confirm_password": "adminpassword123"})
    return client.cookies.get("lifeops_csrf", "")

def test_health_reports_model_unavailable_without_claiming_execution():
    with TestClient(fasthtml_app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_runtime"] == "not_configured"

def test_selfx_ui_exposes_goal_proposal_and_evidence_sections():
    with TestClient(fasthtml_app) as client:
        _login(client)
        response = client.get("/selfx")
    assert response.status_code == 200
    assert "Improvement goal" in response.text
    assert "Improvement proposal" in response.text
    assert "Evaluation history" in response.text

def test_selfx_rejects_empty_goal():
    with TestClient(fasthtml_app) as client:
        csrf = _login(client)
        response = client.post("/selfx/goals", data={"title": "", "objective": ""}, headers={"x-csrf-token": csrf})
    assert response.status_code == 200
    assert "Goal title and objective are required" in response.text

def test_remote_binding_is_always_rejected_until_security_controls_exist():
    import pytest
    with pytest.raises(ValueError, match="Remote binding is disabled"):
        validate_bind_host("0.0.0.0")
    assert validate_bind_host("127.0.0.1") == "127.0.0.1"
