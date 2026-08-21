"""Tests for the encrypted device-bound profile vault."""

import pytest

from app.adapters.sim_cards import SIMWriteError
from app.services.profiles import ProfileVaultService
from app.services.provisioning import ProfileWriteService
from app.models import ProfileInventoryUpdateRequest, ProvisioningDraft

CSV = """IMSI;ICCID;ACC;Ki;OPC;ADM1
001010123456789;8949012345678901234;1;00112233445566778899AABBCCDDEEFF;FFEEDDCCBBAA99887766554433221100;DEADBEEF
"""


def test_profile_vault_encrypts_every_imported_value(tmp_path) -> None:
    database = tmp_path / "profiles.db"
    key = tmp_path / "profile.key"
    service = ProfileVaultService(str(database), str(key))

    result = service.import_csv(CSV)
    profiles = service.list_profiles()

    assert result.imported == 1
    assert profiles[0].iccid == "8949012345678901234"
    raw = database.read_bytes()
    for value in ("8949012345678901234", "001010123456789", "00112233445566778899AABBCCDDEEFF", "FFEEDDCCBBAA99887766554433221100", "DEADBEEF"):
        assert value.encode() not in raw
    assert key.stat().st_mode & 0o777 == 0o600
    assert database.stat().st_mode & 0o777 == 0o600
    assert profiles[0].revision == 1
    revisions = service.list_revisions(profiles[0].id)
    assert [item.revision for item in revisions] == [1]
    draft = service.get_draft(profiles[0].id)
    assert draft.iccid == "8949012345678901234"
    assert draft.ki.get_secret_value() == "00112233445566778899AABBCCDDEEFF"
    secrets = service.get_secrets(profiles[0].id)
    assert secrets["KI"] == "00112233445566778899AABBCCDDEEFF"
    assert "ICCID" not in secrets
    assert secrets["ADM1"] == "DEADBEEF"
    assert "ADM" not in secrets


def test_missing_profile_is_not_found(tmp_path) -> None:
    service = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key"))
    try:
        service.get_draft(999)
    except KeyError:
        pass
    else:
        raise AssertionError("missing profile was returned")


def test_inventory_management_is_encrypted_and_does_not_create_revision(tmp_path) -> None:
    database = tmp_path / "profiles.db"
    service = ProfileVaultService(str(database), str(tmp_path / "profile.key")); service.import_csv(CSV)
    profile = service.list_profiles()[0]

    service.set_inventory(profile.id, "issued", "Max Mustermann", "2026-08-21", "Testgerät im Labor")

    updated = service.list_profiles()[0]
    assert updated.inventory_status == "issued"
    assert updated.issued_to == "Max Mustermann"
    assert updated.issued_at.isoformat() == "2026-08-21"
    assert updated.inventory_note == "Testgerät im Labor"
    assert updated.revision == 1
    raw = database.read_bytes()
    assert b"Max Mustermann" not in raw
    assert "Testgerät im Labor".encode() not in raw

    service.set_inventory(profile.id, "in_stock", None, None, "Zurückgegeben")
    returned = service.list_profiles()[0]
    assert returned.inventory_status == "in_stock"
    assert returned.issued_to is None
    assert returned.issued_at is None
    assert returned.inventory_note == "Zurückgegeben"
    assert returned.revision == 1


def test_inventory_update_request_validates_without_assignment_recursion() -> None:
    issued = ProfileInventoryUpdateRequest(
        password="test-password", status="issued", issued_to="  Max Mustermann  ",
        issued_at="2026-08-21", note="  Testgerät  ",
    )
    assert issued.issued_to == "Max Mustermann"
    assert issued.note == "Testgerät"

    returned = ProfileInventoryUpdateRequest(
        password="test-password", status="in_stock", issued_to="Wird entfernt",
        issued_at="2026-08-21", note="Zurückgegeben",
    )
    assert returned.issued_to is None
    assert returned.issued_at is None


def test_existing_vault_is_backfilled_with_revision_one(tmp_path) -> None:
    database = tmp_path / "profiles.db"; key = tmp_path / "profile.key"
    original = ProfileVaultService(str(database), str(key)); original.import_csv(CSV)
    reopened = ProfileVaultService(str(database), str(key))

    profile = reopened.list_profiles()[0]
    assert profile.revision == 1
    assert len(reopened.list_revisions(profile.id)) == 1


def test_change_is_encrypted_and_does_not_modify_active_profile(tmp_path) -> None:
    database = tmp_path / "profiles.db"; key = tmp_path / "profile.key"
    service = ProfileVaultService(str(database), str(key)); service.import_csv(CSV)
    profile = service.list_profiles()[0]
    new_imsi = "001010987654321"
    new_ki = "11223344556677889900AABBCCDDEEFF"

    summary = service.prepare_change(profile.id, new_imsi, "+491701234567", "00AF", new_ki, None)

    assert summary.base_revision == 1
    assert summary.status == "pending"
    assert summary.changed_fields == ["acc", "imsi", "ki", "msisdn"]
    assert service.get_change_summary(profile.id) == summary
    assert service.list_profiles()[0].pending_change is True
    editable = service.get_editable(profile.id)
    assert editable.pending_change is True
    assert editable.imsi == new_imsi
    assert editable.msisdn == "+491701234567"
    assert editable.acc == "00AF"
    assert editable.changed_fields == ["acc", "imsi", "ki", "msisdn"]
    pending_draft = service.get_change_draft(profile.id)
    assert pending_draft.imsi == new_imsi
    assert pending_draft.ki.get_secret_value() == new_ki
    active = service.get_draft(profile.id)
    assert active.imsi == "001010123456789"
    assert active.acc == "0001"
    assert active.ki.get_secret_value() == "00112233445566778899AABBCCDDEEFF"
    assert service.list_profiles()[0].revision == 1
    assert len(service.list_revisions(profile.id)) == 1
    raw = database.read_bytes()
    assert new_imsi.encode() not in raw
    assert new_ki.encode() not in raw

    assert service.discard_change(profile.id) is True
    assert service.get_change_summary(profile.id) is None
    assert service.list_profiles()[0].pending_change is False
    assert service.get_draft(profile.id).imsi == "001010123456789"
    assert service.get_editable(profile.id).pending_change is False
    try:
        service.get_change_draft(profile.id)
    except KeyError:
        pass
    else:
        raise AssertionError("discarded change draft was returned")


def test_unchanged_profile_cannot_create_change_draft(tmp_path) -> None:
    service = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); service.import_csv(CSV)
    profile = service.list_profiles()[0]

    try:
        service.prepare_change(profile.id, profile.imsi, None, "0001", None, None)
    except ValueError as exc:
        assert str(exc) == "no_changes"
    else:
        raise AssertionError("unchanged profile created a draft")


def test_null_optional_fields_do_not_create_phantom_changes(tmp_path) -> None:
    service = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key"))
    draft = ProvisioningDraft(iccid="8949012345678901234", imsi="001010123456789", acc="0001",
        ki="00112233445566778899AABBCCDDEEFF", opc="FFEEDDCCBBAA99887766554433221100", adm="DEADBEEF")
    profile = service.add_profile(draft)

    change = service.prepare_change(profile.id, draft.imsi, None, "0002", None, None)

    assert change.changed_fields == ["acc"]


def test_verified_write_commits_new_revision(tmp_path) -> None:
    class FakeWriteAdapter:
        def write_standard_fields(self, reader_index, expected_iccid, imsi, acc, msisdn, adm, fields, ki, opc, impi=None, impu=None, ims_domain=None, ist=None):
            assert reader_index == 0
            assert expected_iccid == "8949012345678901234"
            assert imsi == "001010987654321"
            assert adm == "DEADBEEF"
            assert ki == "00112233445566778899AABBCCDDEEFF"
            assert opc == "FFEEDDCCBBAA99887766554433221100"
            return fields

    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    vault.prepare_change(profile.id, "001010987654321", None, "0001", None, None)

    revision, verified = ProfileWriteService(FakeWriteAdapter(), vault).execute(profile.id)

    assert revision == 2
    assert verified == ["imsi"]
    assert vault.get_draft(profile.id).imsi == "001010987654321"
    assert vault.get_change_summary(profile.id) is None
    assert [item.revision for item in vault.list_revisions(profile.id)] == [2, 1]
    assert vault.list_profiles()[0].card_verified is True


def test_verified_auth_key_write_commits_new_revision(tmp_path) -> None:
    class FakeSja5Adapter:
        def write_standard_fields(self, reader_index, expected_iccid, imsi, acc, msisdn, adm, fields, ki, opc, impi=None, impu=None, ims_domain=None, ist=None):
            assert fields == ["ki", "opc"]
            assert ki == "11223344556677889900AABBCCDDEEFF"
            assert opc == "AABBCCDDEEFF00112233445566778899"
            return fields

    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    vault.prepare_change(profile.id, profile.imsi, None, "0001", "11223344556677889900AABBCCDDEEFF", "AABBCCDDEEFF00112233445566778899")

    revision, verified = ProfileWriteService(FakeSja5Adapter(), vault).execute(profile.id)

    assert revision == 2
    assert verified == ["ki", "opc"]
    assert vault.get_change_summary(profile.id) is None


def test_single_profile_is_encrypted_and_duplicate_iccid_is_blocked(tmp_path) -> None:
    database = tmp_path / "profiles.db"
    vault = ProfileVaultService(str(database), str(tmp_path / "profile.key"))
    draft = ProvisioningDraft(iccid="8949012345678901234", imsi="001010123456789", acc="0001",
        ki="00112233445566778899AABBCCDDEEFF", opc="FFEEDDCCBBAA99887766554433221100", adm="DEADBEEF")

    profile = vault.add_profile(draft)

    assert profile.revision == 1
    assert profile.card_verified is False
    assert vault.find_by_iccid(draft.iccid) == profile
    assert draft.iccid.encode() not in database.read_bytes()
    try:
        vault.add_profile(draft)
    except ValueError as exc:
        assert str(exc) == "duplicate_iccid"
    else:
        raise AssertionError("duplicate ICCID was stored")

    verified_database = tmp_path / "verified.db"
    verified_vault = ProfileVaultService(str(verified_database), str(tmp_path / "verified.key"))
    verified_profile = verified_vault.add_profile(draft, card_verified=True)
    assert verified_profile.card_verified is True
    verified_vault.mark_card_verified(verified_profile.id)
    assert verified_vault.list_profiles()[0].card_verified is True


def test_profile_delete_removes_revisions_and_pending_draft(tmp_path) -> None:
    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    vault.prepare_change(profile.id, "001010987654321", None, "0001", None, None)

    try:
        vault.delete_profile(profile.id, "8949000000000000000")
    except ValueError as exc:
        assert str(exc) == "iccid_mismatch"
    else:
        raise AssertionError("profile was deleted with wrong ICCID")
    assert vault.get_change_summary(profile.id) is not None

    vault.delete_profile(profile.id, profile.iccid)

    assert vault.list_profiles() == []
    assert vault.get_change_summary(profile.id) is None
    try:
        vault.list_revisions(profile.id)
    except KeyError:
        pass
    else:
        raise AssertionError("deleted profile revisions remained")


def test_card_imsi_adoption_creates_encrypted_revision(tmp_path) -> None:
    database = tmp_path / "profiles.db"
    vault = ProfileVaultService(str(database), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    new_imsi = "001010987654321"

    revision = vault.adopt_card_imsi(profile.id, profile.iccid, new_imsi)

    updated = vault.list_profiles()[0]
    assert revision == 2
    assert updated.imsi == new_imsi
    assert updated.card_verified is True
    assert [item.revision for item in vault.list_revisions(profile.id)] == [2, 1]
    assert new_imsi.encode() not in database.read_bytes()


def test_card_imsi_adoption_rejects_wrong_card_and_pending_change(tmp_path) -> None:
    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    try:
        vault.adopt_card_imsi(profile.id, "8949000000000000000", "001010987654321")
    except ValueError as exc:
        assert str(exc) == "iccid_mismatch"
    else:
        raise AssertionError("IMSI from wrong card was adopted")

    vault.prepare_change(profile.id, "001010111111111", None, "0001", None, None)
    try:
        vault.adopt_card_imsi(profile.id, profile.iccid, "001010987654321")
    except ValueError as exc:
        assert str(exc) == "pending_change"
    else:
        raise AssertionError("pending draft was overwritten")


def test_optional_ims_fields_are_encrypted_and_backward_compatible(tmp_path) -> None:
    database = tmp_path / "profiles.db"
    vault = ProfileVaultService(str(database), str(tmp_path / "profile.key"))
    ims_csv = CSV.replace(
        "IMSI;ICCID;ACC;Ki;OPC;ADM1",
        "IMSI;ICCID;ACC;Ki;OPC;ADM1;IMPI;IMPU;DOMAIN;IST",
    ).replace(
        ";DEADBEEF\n",
        ";DEADBEEF;user@ims.example;sip:user@ims.example;ims.example;03FF\n",
    )

    vault.import_csv(ims_csv)
    profile = vault.list_profiles()[0]
    editable = vault.get_editable(profile.id)

    assert profile.ims_configured is True
    assert editable.impi == "user@ims.example"
    assert editable.impu == "sip:user@ims.example"
    assert editable.ims_domain == "ims.example"
    assert editable.ist == "03FF"
    raw = database.read_bytes()
    for value in ("user@ims.example", "sip:user@ims.example", "ims.example", "03FF"):
        assert value.encode() not in raw

    legacy = ProfileVaultService(str(tmp_path / "legacy.db"), str(tmp_path / "legacy.key"))
    legacy.import_csv(CSV)
    legacy_profile = legacy.list_profiles()[0]
    assert legacy_profile.ims_configured is False
    assert legacy.get_editable(legacy_profile.id).impi is None


def test_verified_ims_write_commits_new_revision(tmp_path) -> None:
    class FakeImsAdapter:
        def write_standard_fields(self, reader_index, expected_iccid, imsi, acc, msisdn, adm, fields, ki, opc, impi=None, impu=None, ims_domain=None, ist=None):
            assert fields == ["impi", "impu", "ims_domain", "ist"]
            assert impi == "001010123456789@ims.example"
            assert impu == "sip:30006@ims.example"
            assert ims_domain == "ims.example"
            assert ist == "03FF"
            return fields

    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    vault.prepare_change(profile.id, profile.imsi, None, "0001", None, None,
        "001010123456789@ims.example", "sip:30006@ims.example", "ims.example", "03FF")

    revision, verified = ProfileWriteService(FakeImsAdapter(), vault).execute(profile.id)

    assert revision == 2
    assert verified == ["impi", "impu", "ims_domain", "ist"]
    assert vault.get_draft(profile.id).impi == "001010123456789@ims.example"


def test_unsupported_card_error_keeps_revision_and_change_draft(tmp_path) -> None:
    class UnsupportedCardAdapter:
        def write_standard_fields(self, *args, **kwargs):
            raise SIMWriteError("unsupported_card_for_ims", "Kartentyp unterstützt diese Felder nicht")

    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    vault.prepare_change(profile.id, profile.imsi, None, "0001", None, None,
        "001010123456789@ims.example", "sip:30006@ims.example", "ims.example", "03FF")

    with pytest.raises(SIMWriteError, match="Kartentyp unterstützt"):
        ProfileWriteService(UnsupportedCardAdapter(), vault).execute(profile.id)

    assert vault.list_profiles()[0].revision == 1
    assert vault.get_change_summary(profile.id) is not None
    assert vault.get_draft(profile.id).impi is None


def test_invalid_card_file_size_keeps_revision_and_change_draft(tmp_path) -> None:
    class InvalidFileSizeAdapter:
        def write_standard_fields(self, *args, **kwargs):
            raise SIMWriteError("invalid_ist_length", "IST muss exakt der Dateigröße der Karte entsprechen")

    vault = ProfileVaultService(str(tmp_path / "profiles.db"), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    vault.prepare_change(profile.id, profile.imsi, None, "0001", None, None, ist="03FF")

    with pytest.raises(SIMWriteError, match="Dateigröße"):
        ProfileWriteService(InvalidFileSizeAdapter(), vault).execute(profile.id)

    assert vault.list_profiles()[0].revision == 1
    assert vault.get_change_summary(profile.id) is not None
    assert vault.get_draft(profile.id).ist is None


def test_verified_fivegs_write_commits_encrypted_revision(tmp_path) -> None:
    public_key = "A1" * 32
    class FakeFiveGsAdapter:
        def write_standard_fields(self, reader_index, expected_iccid, imsi, acc, msisdn, adm, fields, ki, opc,
            impi=None, impu=None, ims_domain=None, ist=None, routing_indicator=None, protection_scheme=None,
            hn_public_key_id=None, hn_public_key=None):
            assert fields == ["hn_public_key", "hn_public_key_id", "protection_scheme", "routing_indicator"]
            assert routing_indicator == "1234"
            assert protection_scheme == 1
            assert hn_public_key_id == 7
            assert hn_public_key == public_key
            return fields

    database = tmp_path / "profiles.db"
    vault = ProfileVaultService(str(database), str(tmp_path / "profile.key")); vault.import_csv(CSV)
    profile = vault.list_profiles()[0]
    vault.prepare_change(profile.id, profile.imsi, None, "0001", None, None,
        routing_indicator="1234", protection_scheme=1, hn_public_key_id=7, hn_public_key=public_key)

    editable = vault.get_editable(profile.id)
    assert editable.routing_indicator == "1234"
    assert editable.protection_scheme == 1
    assert editable.hn_public_key_id == 7
    assert editable.hn_public_key == public_key
    for value in (b"1234", public_key.encode()):
        assert value not in database.read_bytes()

    revision, verified = ProfileWriteService(FakeFiveGsAdapter(), vault).execute(profile.id)

    assert revision == 2
    assert verified == ["hn_public_key", "hn_public_key_id", "protection_scheme", "routing_indicator"]
