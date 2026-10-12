"""End-to-end tests for the API's first-run auth and session cookie."""
from lifeops.storage.models import User


def test_private_api_requires_setup_and_authentication(client):
    response = client.get("/api/v1/system/identity")
    assert response.status_code == 401
    assert response.json()["detail"] == "Initial administrator setup required"


def test_api_bootstrap_login_and_cookie_auth(client, db):
    password = "a sufficiently long test password"
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "api_admin", "password": password},
    )
    assert response.status_code == 200
    assert db.query(User).filter_by(username="api_admin").one().password_hash
    assert response.json()["role"] == "admin"

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "api_admin", "password": password},
    )
    assert login.status_code == 200
    token = client.cookies.get("lifeops_session")
    assert token
    assert len(token) >= 40

    identity = client.get("/api/v1/system/identity")
    assert identity.status_code == 200

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    denied = client.get("/api/v1/system/identity")
    assert denied.status_code == 401


def test_api_bootstrap_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "api_admin", "password": "short"},
    )
    assert response.status_code == 422
