"""End-to-end tests for the API's first-run auth and session cookie."""
from lifeops.storage.models import User


def test_private_api_requires_setup_and_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/system/identity")
    assert response.status_code == 401
    assert response.json()["detail"] == "Initial administrator setup required"


def test_api_bootstrap_login_and_cookie_auth(unauthenticated_client, db):
    password = "a sufficiently long test password"
    response = unauthenticated_client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "api_admin", "password": password},
    )
    assert response.status_code == 200
    assert db.query(User).filter_by(username="api_admin").one().password_hash
    assert response.json()["role"] == "admin"

    login = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "api_admin", "password": password},
    )
    assert login.status_code == 200
    token = unauthenticated_client.cookies.get("lifeops_session")
    assert token
    assert len(token) >= 40

    identity = unauthenticated_client.get("/api/v1/system/identity")
    assert identity.status_code == 200

    logout = unauthenticated_client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    denied = unauthenticated_client.get("/api/v1/system/identity")
    assert denied.status_code == 401


def test_api_bootstrap_rejects_weak_password(unauthenticated_client):
    response = unauthenticated_client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "api_admin", "password": "short"},
    )
    assert response.status_code == 422
