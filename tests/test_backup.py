"""Tests for encrypted removable-media backups."""

import hashlib
import io
import json
from pathlib import Path
import zipfile

from app.services.audit import AuditService
from app.services.backup import AAD, MAGIC, BackupError, BackupService


def test_backup_is_encrypted_and_contains_valid_manifest(tmp_path, monkeypatch) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    monkeypatch.setattr("app.services.backup.os.path.ismount", lambda path: Path(path) == tmp_path)
    audit = AuditService(":memory:")
    audit.record("sim.read", "success")
    service = BackupService(audit, mount_roots=(tmp_path,))
    password = "safe-backup-password"

    result = service.create(str(tmp_path), password)

    blob = (tmp_path / result.filename).read_bytes()
    assert blob.startswith(MAGIC)
    assert b"sim.read" not in blob
    salt = blob[len(MAGIC):len(MAGIC) + 16]
    nonce = blob[len(MAGIC) + 16:len(MAGIC) + 28]
    ciphertext = blob[len(MAGIC) + 28:]
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    payload = AESGCM(key).decrypt(nonce, ciphertext, AAD)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        database = archive.read("database/audit.db")
    assert manifest["encryption"] == "AES-256-GCM"
    assert manifest["contents"]["database/audit.db"]["sha256"] == hashlib.sha256(database).hexdigest()
    assert result.verified is True


def test_backup_rejects_unapproved_target(tmp_path) -> None:
    service = BackupService(AuditService(":memory:"), mount_roots=())

    try:
        service.create(str(tmp_path), "safe-backup-password")
    except BackupError as exc:
        assert exc.code == "invalid_target"
    else:
        raise AssertionError("unapproved backup target was accepted")
