"""Tests for the encrypted central SUCI public-key catalogue."""

import pytest

from app.models import ProvisioningDraft
from app.services.profiles import ProfileVaultService


def test_suci_key_catalogue_encrypts_and_changes_status(tmp_path) -> None:
    database = tmp_path / "profiles.db"
    vault = ProfileVaultService(str(database), str(tmp_path / "profile.key"))
    key_hex = "A1" * 32

    imported = vault.import_suci_key("Open5GS Profile A", 1, 1, key_hex)
    assert imported.public_key == key_hex
    assert imported.active is True
    assert imported.in_use is False
    assert key_hex.encode() not in database.read_bytes()
    assert vault.set_suci_key_active(imported.id, False).active is False

    with pytest.raises(ValueError, match="duplicate_key_id"):
        vault.import_suci_key("Doppelt", 1, 1, "A2" * 32)


def test_private_key_material_is_rejected(tmp_path) -> None:
    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key"))
    with pytest.raises(ValueError, match="Private Schlüssel"):
        vault.import_suci_key("Nicht erlaubt", 1, 1, "-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----")


def test_suci_key_used_by_profile_cannot_be_deleted(tmp_path) -> None:
    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key"))
    key_hex = "A1" * 32
    imported = vault.import_suci_key("Open5GS Profile A", 1, 1, key_hex)
    vault.add_profile(ProvisioningDraft(
        iccid="8949012345678901234", imsi="001010123456789",
        ki="00112233445566778899AABBCCDDEEFF", opc="FFEEDDCCBBAA99887766554433221100",
        adm="DEADBEEF", routing_indicator="0000", protection_scheme=1,
        hn_public_key_id=1, hn_public_key=key_hex,
    ))

    assert vault.list_suci_keys()[0].in_use is True
    with pytest.raises(ValueError, match="key_in_use"):
        vault.delete_suci_key(imported.id)
