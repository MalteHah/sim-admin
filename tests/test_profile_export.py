"""Tests for the redacted profile inventory export."""

from datetime import UTC, datetime
from fastapi.testclient import TestClient

from app.core.dependencies import get_profile_vault_service
from app.main import app
from app.models import ProfileSummary


class FakeVault:
    def list_profiles(self) -> list[ProfileSummary]:
        return [ProfileSummary(id=1, created_at=datetime.now(UTC), iccid="8949012345678901234", imsi="001010123456789", ki_configured=True, opc_configured=True, adm_configured=True)]


def test_inventory_export_contains_no_secret_values() -> None:
    app.dependency_overrides[get_profile_vault_service] = FakeVault
    client = TestClient(app)
    try:
        assert client.post("/login", json={"username": "admin", "password": "correct-horse-battery-staple"}).status_code == 200
        response = client.get("/api/v1/profiles/export")
    finally:
        app.dependency_overrides.pop(get_profile_vault_service, None)

    assert response.status_code == 200
    assert "8949012345678901234" in response.text
    assert "Ki vorhanden" in response.text
    assert "00112233445566778899AABBCCDDEEFF" not in response.text
    assert response.headers["cache-control"].startswith("no-store")
