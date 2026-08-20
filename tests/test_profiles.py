"""Tests for the encrypted device-bound profile vault."""

from app.services.profiles import ProfileVaultService
from app.services.provisioning import ProfileWriteService
from app.models import ProvisioningDraft

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


def test_verified_write_commits_new_revision(tmp_path) -> None:
    class FakeWriteAdapter:
        def write_standard_fields(self, reader_index, expected_iccid, imsi, acc, msisdn, adm, fields, ki, opc):
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
        def write_standard_fields(self, reader_index, expected_iccid, imsi, acc, msisdn, adm, fields, ki, opc):
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
