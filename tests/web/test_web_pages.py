import pytest
from starlette.testclient import TestClient
from lifeops.web.app_ui import app

def test_web_pages_routing():
    client = TestClient(app)

    pages = [
        "/", "/assistant", "/tasks", "/calendar", "/notes", "/memory",
        "/research", "/skills", "/selfx", "/workflows", "/workers",
        "/files", "/tools", "/models", "/security", "/analytics",
        "/backups", "/notifications", "/settings", "/help"
    ]

    for path in pages:
        res = client.get(path)
        assert res.status_code == 200, f"Failed for page: {path}"
        assert "LifeOps AI" in res.text
