"""API tests for reader discovery."""

from fastapi.testclient import TestClient

from app.adapters.readers import ReaderAdapterError
from app.core.dependencies import get_reader_service
from app.main import app
from app.models import Reader, ReaderStatus
from app.services.readers import ReaderService

client = TestClient(app)


def login() -> None:
    response = client.post(
        "/login",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200


class FakeReaderAdapter:
    def list_readers(self) -> list[Reader]:
        return [
            Reader(
                name="Test Reader 00 00",
                reader_type="pcsc",
                status=ReaderStatus.CARD_PRESENT,
                atr="3B 00",
            )
        ]


class FailingReaderAdapter:
    def list_readers(self) -> list[Reader]:
        raise ReaderAdapterError("PC/SC unavailable")


def test_list_readers() -> None:
    login()
    app.dependency_overrides[get_reader_service] = lambda: ReaderService(
        FakeReaderAdapter()
    )
    try:
        response = client.get("/api/v1/readers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "Test Reader 00 00",
            "reader_type": "pcsc",
            "status": "card_present",
            "atr": "3B 00",
        }
    ]


def test_reader_failure_returns_service_unavailable() -> None:
    login()
    app.dependency_overrides[get_reader_service] = lambda: ReaderService(
        FailingReaderAdapter()
    )
    try:
        response = client.get("/api/v1/readers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "PC/SC unavailable"}
