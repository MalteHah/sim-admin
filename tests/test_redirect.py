"""Tests for the legacy HTTP redirect service."""

from fastapi.testclient import TestClient

from app.redirect import app


def test_redirect_preserves_path_and_query() -> None:
    response = TestClient(app).get(
        "/settings?section=security", follow_redirects=False
    )

    assert response.status_code == 308
    assert response.headers["location"] == "https://testserver:8443/settings?section=security"
