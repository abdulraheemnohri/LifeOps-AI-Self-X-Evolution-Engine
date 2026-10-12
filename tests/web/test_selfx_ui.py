from starlette.testclient import TestClient
from lifeops.app import app

def test_health_reports_model_unavailable_without_claiming_execution():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_runtime"] == "not_configured"

def test_selfx_ui_exposes_goal_proposal_and_evidence_sections():
    with TestClient(app) as client:
        response = client.get("/selfx")
    assert response.status_code == 200
    assert "Improvement goal" in response.text
    assert "Improvement proposal" in response.text
    assert "Evaluation history" in response.text

def test_selfx_rejects_empty_goal():
    with TestClient(app) as client:
        response = client.post("/selfx/goals", data={"title": "", "objective": ""})
    assert response.status_code == 200
    assert "Goal title and objective are required" in response.text
