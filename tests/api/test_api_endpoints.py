import pytest

def test_api_endpoints(auth_client):
    client = auth_client

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
