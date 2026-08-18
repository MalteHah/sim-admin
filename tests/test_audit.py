"""Tests for the metadata-only activity trail."""

from fastapi.testclient import TestClient

from app.core.dependencies import get_audit_service
from app.main import app
from app.services.audit import AuditService


def test_audit_service_returns_newest_event_first() -> None:
    audit = AuditService(":memory:")
    audit.record("auth.login", "success")
    audit.record("provisioning.preview", "success", "dry-run")

    events = audit.list_recent()

    assert [event.action for event in events] == [
        "provisioning.preview",
        "auth.login",
    ]


def test_preview_audit_never_contains_subscriber_or_secret_values() -> None:
    audit = AuditService(":memory:")
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)
    draft = {
        "iccid": "8949012345678901234",
        "imsi": "001010123456789",
        "msisdn": "+491701234567",
        "acc": "0001",
        "ki": "00112233445566778899AABBCCDDEEFF",
        "opc": "FFEEDDCCBBAA99887766554433221100",
        "adm": "DEADBEEF",
    }
    try:
        login = client.post(
            "/login",
            json={"username": "admin", "password": "correct-horse-battery-staple"},
        )
        assert login.status_code == 200
        preview = client.post("/api/v1/provisioning/preview", json=draft)
        assert preview.status_code == 200
        response = client.get("/api/v1/audit")
    finally:
        app.dependency_overrides.pop(get_audit_service, None)

    assert response.status_code == 200
    serialized = response.text
    for field in ("iccid", "imsi", "msisdn", "ki", "opc", "adm"):
        sensitive_value = draft[field]
        assert sensitive_value not in serialized
    assert any(
        event["action"] == "provisioning.preview" for event in response.json()
    )


def test_activity_page_requires_authentication() -> None:
    response = TestClient(app).get("/activity", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
