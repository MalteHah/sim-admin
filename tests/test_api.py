"""Smoke tests for the initial API."""

from fastapi.testclient import TestClient

from app.core.version import application_version
from app.main import app

client = TestClient(app)


def authenticated_client() -> TestClient:
    authenticated = TestClient(app)
    response = authenticated.post(
        "/login",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return authenticated


def test_dashboard() -> None:
    response = authenticated_client().get("/")

    assert response.status_code == 200
    assert "SIM-Admin" in response.text
    assert f"SIM-Admin {application_version()}" in response.text
    assert "Kartenleser" in response.text


def test_profile_vault_page_is_authenticated() -> None:
    response = authenticated_client().get("/profiles")

    assert response.status_code == 200
    assert "Profiltresor" in response.text


def test_api_information() -> None:
    response = authenticated_client().get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"application": "sim-admin", "version": application_version()}


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_redirects_to_login() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_api_requires_login() -> None:
    response = client.get("/api/v1/readers")

    assert response.status_code == 401


def test_login_rejects_wrong_password() -> None:
    response = client.post(
        "/login", json={"username": "admin", "password": "wrong-password"}
    )

    assert response.status_code == 401
