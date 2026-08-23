"""Tests for the non-writing provisioning preview."""

from fastapi.testclient import TestClient

from app.core.dependencies import get_card_comparison_service
from app.main import app
from app.models import CardComparisonRequest, SIMReadResult
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


def test_single_card_preview_includes_optional_ims_and_fivegs_steps() -> None:
    login()
    draft = valid_draft() | {
        "impi": "001010123456789@ims.example",
        "impu": "sip:900002@ims.example",
        "ims_domain": "ims.example",
        "ist": "03FF",
        "routing_indicator": "1234",
        "protection_scheme": 1,
        "hn_public_key_id": 7,
        "hn_public_key": "A1" * 32,
    }

    response = client.post("/api/v1/provisioning/preview", json=draft)

    assert response.status_code == 200
    actions = [step["action"] for step in response.json()["steps"]]
    assert "IMS-Profildaten vormerken" in actions
    assert "5GS-/SUCI-Profildaten vormerken" in actions


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


class FakeSuciCardAdapter(FakeCardAdapter):
    def read_identity(self, reader_index: int = 0) -> SIMReadResult:
        return SIMReadResult(
            reader_index=reader_index, card_type="SysmocomSJA5", atr="3B 00",
            iccid="8949012345678901234", imsi="001010123456789",
            suci_supported=True, suci_readable=True, routing_indicator="0000",
            protection_scheme=1, hn_public_key_id=1, hn_public_key="A1" * 32,
            suci_service_124_active=True, suci_service_125_active=False,
            ims_supported=True, ims_readable=True,
            impi="001010123456789@ims.example", impu="sip:123@ims.example",
            ims_domain="ims.example", ist="190208",
        )


def test_card_comparison_includes_matching_suci_configuration() -> None:
    service = CardComparisonService(FakeSuciCardAdapter())
    result = service.compare(CardComparisonRequest(
        target_iccid="8949012345678901234", target_imsi="001010123456789",
        target_routing_indicator="0000", target_protection_scheme=1,
        target_hn_public_key_id=1, target_hn_public_key="A1" * 32,
    ))

    assert result.suci_compared is True
    assert result.suci_matches is True
    assert result.suci_service_124_active is True
    assert result.suci_service_125_active is False


def test_card_comparison_exposes_all_suci_priorities() -> None:
    adapter = FakeSuciCardAdapter()
    original = adapter.read_identity
    def read_with_priorities(reader_index: int = 0) -> SIMReadResult:
        result = original(reader_index)
        result.suci_configurations = [
            {"priority": 0, "protection_scheme": 1, "hn_public_key_id": 1, "hn_public_key": "A1" * 32},
            {"priority": 1, "protection_scheme": 0},
        ]
        return result
    adapter.read_identity = read_with_priorities

    result = CardComparisonService(adapter).compare(CardComparisonRequest(
        target_iccid="8949012345678901234", target_imsi="001010123456789",
    ))

    assert [item["priority"] for item in result.current_suci_configurations] == [0, 1]


def test_card_comparison_includes_matching_ims_configuration() -> None:
    service = CardComparisonService(FakeSuciCardAdapter())
    result = service.compare(CardComparisonRequest(
        target_iccid="8949012345678901234", target_imsi="001010123456789",
        compare_ims=True, target_impi="001010123456789@ims.example",
        target_impu="sip:123@ims.example", target_ims_domain="ims.example", target_ist="190208",
    ))

    assert result.ims_compared is True
    assert result.ims_matches is True


def test_card_comparison_includes_readable_acc_and_msisdn() -> None:
    class FakeStandardFieldAdapter(FakeCardAdapter):
        def read_identity(self, reader_index: int = 0) -> SIMReadResult:
            result = super().read_identity(reader_index)
            result.acc_readable = True; result.acc = "0004"
            result.msisdn_readable = True; result.msisdn = "491701234567"
            return result

    result = CardComparisonService(FakeStandardFieldAdapter()).compare(CardComparisonRequest(
        target_iccid="8949012345678901234", target_imsi="001010123456789",
        compare_standard_fields=True, target_acc="0004", target_msisdn="+491701234567",
    ))

    assert result.acc_matches is True
    assert result.msisdn_matches is True
    assert result.current_acc == "0004"
    assert result.current_msisdn == "491701234567"


def test_null_scheme_does_not_require_suci_ust_services() -> None:
    class FakeNullSchemeAdapter(FakeCardAdapter):
        def read_identity(self, reader_index: int = 0) -> SIMReadResult:
            result = super().read_identity(reader_index)
            result.suci_supported = True; result.suci_readable = True
            result.routing_indicator = "0000"; result.protection_scheme = 0
            result.suci_service_124_active = False; result.suci_service_125_active = False
            return result

    result = CardComparisonService(FakeNullSchemeAdapter()).compare(CardComparisonRequest(
        target_iccid="8949012345678901234", target_imsi="001010123456789",
        compare_suci=True, target_routing_indicator="0000", target_protection_scheme=0,
    ))

    assert result.suci_managed is True
    assert result.suci_matches is True


def test_card_comparison_accepts_fully_cleared_ims_configuration() -> None:
    class FakeClearedImsCardAdapter(FakeCardAdapter):
        def read_identity(self, reader_index: int = 0) -> SIMReadResult:
            result = super().read_identity(reader_index)
            result.ims_supported = True
            result.ims_readable = True
            return result

    service = CardComparisonService(FakeClearedImsCardAdapter())
    result = service.compare(CardComparisonRequest(
        target_iccid="8949012345678901234", target_imsi="001010123456789", compare_ims=True,
    ))

    assert result.ims_readable is True
    assert result.ims_matches is None
