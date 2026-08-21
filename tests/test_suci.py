"""Tests for the SJA5 SUCI-by-ME card representation."""

import pytest
from pydantic import ValidationError

from app.adapters.suci import build_suci_calc_info, enable_suci_by_me
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
