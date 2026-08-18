"""Tests for the non-writing provisioning preview."""

from fastapi.testclient import TestClient

from app.core.dependencies import get_card_comparison_service
from app.main import app
from app.models import SIMReadResult
from app.services.provisioning import CardComparisonService

client = TestClient(app)


def login() -> None:
    response = client.post(
        "/login",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200


def valid_draft() -> dict[str, str]:
    return {
        "iccid": "8949012345678901234",
        "imsi": "001010123456789",
        "msisdn": "+491701234567",
        "acc": "0001",
        "ki": "00112233445566778899AABBCCDDEEFF",
        "opc": "FFEEDDCCBBAA99887766554433221100",
        "adm": "DEADBEEF",
    }


def test_preview_is_redacted_and_does_not_write() -> None:
    login()
    draft = valid_draft()
    response = client.post("/api/v1/provisioning/preview", json=draft)

    assert response.status_code == 200
    preview = response.json()
    assert preview["mode"] == "dry-run"
    assert preview["write_performed"] is False
    assert preview["ki_configured"] is True
    serialized = response.text
    assert draft["ki"] not in serialized
    assert draft["opc"] not in serialized
    assert draft["adm"] not in serialized


def test_preview_rejects_invalid_hex_key() -> None:
    login()
    draft = valid_draft()
    draft["ki"] = "Z" * 32

    response = client.post("/api/v1/provisioning/preview", json=draft)

    assert response.status_code == 422


class FakeCardAdapter:
    def read_identity(self, reader_index: int = 0) -> SIMReadResult:
        return SIMReadResult(
            reader_index=reader_index,
            card_type="UICC",
            atr="3B 00",
            iccid="8949012345678901234",
            imsi="001010123456789",
        )


def test_card_comparison_matches_without_write() -> None:
    login()
    app.dependency_overrides[get_card_comparison_service] = lambda: (
        CardComparisonService(FakeCardAdapter())
    )
    try:
        response = client.post(
            "/api/v1/provisioning/card-comparison",
            json={
                "reader_index": 0,
                "target_iccid": "8949012345678901234",
                "target_imsi": "001010123456789",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert result["iccid_matches"] is True
    assert result["imsi_matches"] is True
    assert result["write_performed"] is False


def test_card_comparison_marks_differences() -> None:
    login()
    app.dependency_overrides[get_card_comparison_service] = lambda: (
        CardComparisonService(FakeCardAdapter())
    )
    try:
        response = client.post(
            "/api/v1/provisioning/card-comparison",
            json={
                "reader_index": 0,
                "target_iccid": "8949099999999999999",
                "target_imsi": "001019999999999",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["iccid_matches"] is False
    assert response.json()["imsi_matches"] is False
