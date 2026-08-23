"""Tests for the SJA5 SUCI-by-ME card representation."""

import pytest
from pydantic import ValidationError

from app.adapters.suci import build_s17_usim_suci_calc_info, build_suci_calc_info, build_suci_calc_info_list, enable_suci_by_me, enable_suci_by_usim
from app.models import ProvisioningDraft


BASE_DRAFT = {
    "iccid": "8949012345678901234",
    "imsi": "001010123456789",
    "ki": "00112233445566778899AABBCCDDEEFF",
    "opc": "FFEEDDCCBBAA99887766554433221100",
    "adm": "DEADBEEF",
}


def test_profile_a_uses_list_index_one_and_keeps_open5gs_key_id() -> None:
    target = build_suci_calc_info(1, 7, "A1" * 32)

    assert target["prot_scheme_id_list"] == [
        {"priority": 0, "identifier": 1, "key_index": 1}
    ]
    assert target["hnet_pubkey_list"][0]["hnet_pubkey_identifier"] == 7
    assert target["hnet_pubkey_list"][0]["hnet_pubkey"] == bytes.fromhex("A1" * 32)


def test_null_scheme_has_no_home_network_key() -> None:
    assert build_suci_calc_info(0, None, None) == {
        "prot_scheme_id_list": [{"priority": 0, "identifier": 0, "key_index": 0}],
        "hnet_pubkey_list": [],
    }


def test_suci_by_me_enables_124_and_disables_125() -> None:
    assert enable_suci_by_me([2, 124, 125, 126]) == [2, 124, 126]


def test_suci_by_me_updates_structured_pysim_ust() -> None:
    current = {124: {"activated": False, "description": "privacy"},
        125: {"activated": True, "description": "on-card"}}
    updated = enable_suci_by_me(current)
    assert updated[124]["activated"] is True
    assert updated[125]["activated"] is False
    assert current[124]["activated"] is False


def test_suci_by_usim_enables_both_124_and_125() -> None:
    assert enable_suci_by_usim([2, 126]) == [2, 124, 125, 126]


def test_s17_usim_accepts_only_uncompressed_profile_b() -> None:
    target = build_s17_usim_suci_calc_info(2, 2, "04" + "A1" * 64)
    assert target["prot_scheme_id_list"][0]["identifier"] == 2
    with pytest.raises(ValueError, match="Profile B"):
        build_s17_usim_suci_calc_info(1, 1, "A1" * 32)
    with pytest.raises(ValueError, match="uncompressed"):
        build_s17_usim_suci_calc_info(2, 2, "02" + "A1" * 32)


def test_multiple_suci_configurations_keep_priority_and_key_indexes() -> None:
    target = build_suci_calc_info_list([
        {"priority": 2, "protection_scheme": 0},
        {"priority": 0, "protection_scheme": 1, "hn_public_key_id": 1, "hn_public_key": "A1" * 32},
        {"priority": 1, "protection_scheme": 2, "hn_public_key_id": 2, "hn_public_key": "04" + "B2" * 64},
    ])

    assert target["prot_scheme_id_list"] == [
        {"priority": 0, "identifier": 1, "key_index": 1},
        {"priority": 1, "identifier": 2, "key_index": 2},
        {"priority": 2, "identifier": 0, "key_index": 0},
    ]
    assert [item["hnet_pubkey_identifier"] for item in target["hnet_pubkey_list"]] == [1, 2]


def test_multiple_suci_configurations_reject_duplicate_priority() -> None:
    with pytest.raises(ValueError, match="priorities"):
        build_suci_calc_info_list([
            {"priority": 0, "protection_scheme": 0},
            {"priority": 0, "protection_scheme": 0},
        ])


def test_multiple_suci_configurations_reject_duplicate_entries() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        build_suci_calc_info_list([
            {"priority": 0, "protection_scheme": 0},
            {"priority": 1, "protection_scheme": 0},
        ])


def test_suci_configuration_requires_routing_indicator() -> None:
    with pytest.raises(ValidationError, match="routing_indicator is required"):
        ProvisioningDraft(
            **BASE_DRAFT, protection_scheme=1, hn_public_key_id=1,
            hn_public_key="A1" * 32,
        )


def test_profile_a_with_routing_indicator_is_valid() -> None:
    draft = ProvisioningDraft(
        **BASE_DRAFT, routing_indicator="0000", protection_scheme=1,
        hn_public_key_id=1, hn_public_key="A1" * 32,
    )
    assert draft.routing_indicator == "0000"


def test_usim_mode_requires_profile_b_and_uncompressed_key() -> None:
    draft = ProvisioningDraft(**BASE_DRAFT, routing_indicator="0000", suci_calculation_mode="usim",
        protection_scheme=2, hn_public_key_id=2, hn_public_key="04" + "A1" * 64)
    assert draft.suci_calculation_mode == "usim"
    with pytest.raises(ValidationError, match="scheme B"):
        ProvisioningDraft(**BASE_DRAFT, routing_indicator="0000", suci_calculation_mode="usim",
            protection_scheme=1, hn_public_key_id=1, hn_public_key="A1" * 32)


def test_me_mode_accepts_multiple_ordered_configurations() -> None:
    draft = ProvisioningDraft(**BASE_DRAFT, routing_indicator="0000", suci_configurations=[
        {"priority": 2, "protection_scheme": 0},
        {"priority": 0, "protection_scheme": 1, "hn_public_key_id": 1, "hn_public_key": "A1" * 32},
    ])
    assert draft.protection_scheme == 1
    assert len(draft.suci_configurations) == 2
    with pytest.raises(ValidationError, match="exactly one"):
        ProvisioningDraft(**BASE_DRAFT, routing_indicator="0000", suci_calculation_mode="usim",
            suci_configurations=[{"priority": 0, "protection_scheme": 2, "hn_public_key_id": 2, "hn_public_key": "04" + "A1" * 64},
                {"priority": 1, "protection_scheme": 0}])
