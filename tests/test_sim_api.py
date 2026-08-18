"""Tests for the protected, read-only SIM identity endpoint."""

from fastapi.testclient import TestClient

from app.adapters.sim_cards import SIMReadError
from app.core.dependencies import get_sim_card_service
from app.main import app
from app.models import SIMReadResult
from app.services.sim_cards import SIMCardService

client = TestClient(app)


class FakeSIMCardAdapter:
    def read_identity(self, reader_index: int = 0) -> SIMReadResult:
        return SIMReadResult(
            reader_index=reader_index,
            card_type="UICC",
            atr="3B 00",
            iccid="8949012345678901234",
            imsi="001010123456789",
        )


class EmptyReaderAdapter:
    def read_identity(self, reader_index: int = 0) -> SIMReadResult:
        raise SIMReadError("no_card", "Keine SIM-Karte eingelegt")


def login() -> None:
    response = client.post(
        "/login",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200


def test_read_sim_identity() -> None:
    login()
    app.dependency_overrides[get_sim_card_service] = lambda: SIMCardService(
        FakeSIMCardAdapter()
    )
    try:
        response = client.post("/api/v1/sim/read?reader_index=0")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["iccid"] == "8949012345678901234"
    assert response.json()["imsi"] == "001010123456789"


def test_read_sim_without_card() -> None:
    login()
    app.dependency_overrides[get_sim_card_service] = lambda: SIMCardService(
        EmptyReaderAdapter()
    )
    try:
        response = client.post("/api/v1/sim/read")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "no_card"
