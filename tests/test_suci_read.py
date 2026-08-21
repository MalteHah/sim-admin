"""Tests for normalizing SJA5 SUCI files during read-only inspection."""

from app.adapters.suci import read_suci_card_state


def test_read_suci_card_state_resolves_key_index_and_ust() -> None:
    state = read_suci_card_state(
        {"routing_indicator": "0000"},
        {
            "prot_scheme_id_list": [{"priority": 0, "identifier": 1, "key_index": 1}],
            "hnet_pubkey_list": [{"hnet_pubkey_identifier": 7, "hnet_pubkey": bytes.fromhex("A1" * 32)}],
        },
        {124: {"activated": True}, 125: {"activated": False}},
    )

    assert state == {
        "routing_indicator": "0000", "protection_scheme": 1,
        "hn_public_key_id": 7, "hn_public_key": "A1" * 32,
        "suci_service_124_active": True, "suci_service_125_active": False,
    }
