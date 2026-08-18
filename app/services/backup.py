"""Encrypted, integrity-checked backup creation for removable media."""

from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from app.models import BackupFile, BackupInspection, BackupResult, BackupTarget
from app.services.audit import AuditService
from app.services.profiles import ProfileVaultService

MAGIC = b"SIMADMIN1"
AAD = b"sim-admin-backup-v1"


class BackupError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class BackupService:
    """Discover safe targets and create AES-256-GCM encrypted archives."""

    def __init__(
        self,
        audit: AuditService,
        mount_roots: tuple[Path, ...] | None = None,
        profiles: ProfileVaultService | None = None,
    ) -> None:
        self._audit = audit
        self._profiles = profiles
        configured = os.getenv("SIM_ADMIN_BACKUP_MOUNT_ROOTS")
        if mount_roots is not None:
            self._mount_roots = mount_roots
        elif configured:
            self._mount_roots = tuple(Path(item) for item in configured.split(":"))
        else:
            self._mount_roots = (Path("/media"), Path("/run/media"), Path("/mnt"))

    def list_targets(self) -> list[BackupTarget]:
        targets: list[BackupTarget] = []
        for root in self._mount_roots:
            if not root.exists():
                continue
            candidates = [root, *root.rglob("*")]
            for candidate in candidates:
                if not candidate.is_dir() or not os.path.ismount(candidate):
                    continue
                try:
                    usage = shutil.disk_usage(candidate)
                except OSError:
                    continue
                targets.append(
                    BackupTarget(
                        path=str(candidate.resolve()),
                        name=candidate.name or str(candidate),
                        free_bytes=usage.free,
                    )
                )
        return sorted(targets, key=lambda target: target.name.casefold())

    def create(self, target_path: str, password: str) -> BackupResult:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if len(password) < 12:
            raise BackupError("weak_password", "Das Backup-Passwort muss mindestens 12 Zeichen haben")
        allowed = {target.path for target in self.list_targets()}
        resolved = str(Path(target_path).resolve())
        if resolved not in allowed:
            raise BackupError("invalid_target", "Der ausgewählte Datenträger ist nicht verfügbar")

        created_at = datetime.now(UTC)
        filename = f"sim-admin-backup-{created_at:%Y-%m-%d_%H%M%S}.sab"
        destination = Path(resolved) / filename
        payload = self._build_payload(created_at)
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        encrypted = AESGCM(key).encrypt(nonce, payload, AAD)
        blob = MAGIC + salt + nonce + encrypted

        temporary = destination.with_suffix(".tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            if temporary.read_bytes() != blob:
                raise BackupError("verification_failed", "Die Sicherung konnte nicht verifiziert werden")
            temporary.replace(destination)
        except FileExistsError as exc:
            raise BackupError("already_exists", "Eine Sicherung mit diesem Namen existiert bereits") from exc
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise BackupError("write_failed", "Die Sicherung konnte nicht geschrieben werden") from exc

        return BackupResult(
            filename=filename,
            size_bytes=len(blob),
            verified=True,
        )

    def list_files(self) -> list[BackupFile]:
        files: list[BackupFile] = []
        for target in self.list_targets():
            for backup in Path(target.path).glob("sim-admin-backup-*.sab"):
                if backup.is_file():
                    files.append(BackupFile(target_path=target.path, filename=backup.name, size_bytes=backup.stat().st_size))
        return sorted(files, key=lambda item: item.filename, reverse=True)

    def inspect(self, target_path: str, filename: str, password: str) -> BackupInspection:
        manifest, _ = self._read_verified(target_path, filename, password)
        return BackupInspection(
            filename=filename,
            created_at=manifest["created_at"],
            format_version=manifest["format_version"],
            contents=list(manifest["contents"]),
            integrity_valid=True,
        )

    def restore(self, target_path: str, filename: str, password: str, confirmation: str) -> BackupInspection:
        if confirmation != "WIEDERHERSTELLEN":
            raise BackupError("confirmation_required", "Die Sicherheitsbestätigung fehlt")
        manifest, files = self._read_verified(target_path, filename, password)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "audit.db"
            source.write_bytes(files["database/audit.db"])
            self._audit.restore(source)
            if self._profiles and "database/profiles.db" in files and "config/profile.key" in files:
                profile_db = Path(directory) / "profiles.db"; profile_key = Path(directory) / "profile.key"
                profile_db.write_bytes(files["database/profiles.db"]); profile_key.write_bytes(files["config/profile.key"])
                self._profiles.restore(profile_db, profile_key)
        return BackupInspection(filename=filename, created_at=manifest["created_at"], format_version=1, contents=list(manifest["contents"]), integrity_valid=True)

    def _read_verified(self, target_path: str, filename: str, password: str) -> tuple[dict, dict[str, bytes]]:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        allowed = {target.path for target in self.list_targets()}
        resolved = str(Path(target_path).resolve())
        if resolved not in allowed or Path(filename).name != filename or not filename.endswith(".sab"):
            raise BackupError("invalid_backup", "Die Backup-Datei ist nicht zulässig")
        blob = (Path(resolved) / filename).read_bytes()
        if len(blob) > 50 * 1024 * 1024 or not blob.startswith(MAGIC):
            raise BackupError("invalid_backup", "Das Backup-Format ist ungültig")
        salt, nonce, ciphertext = blob[9:25], blob[25:37], blob[37:]
        key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        try:
            payload = AESGCM(key).decrypt(nonce, ciphertext, AAD)
        except InvalidTag as exc:
            raise BackupError("decryption_failed", "Passwort falsch oder Backup beschädigt") from exc
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                allowed_names = {"manifest.json", "database/audit.db", "database/profiles.db", "config/profile.key"}
                if not set(archive.namelist()).issubset(allowed_names) or "database/audit.db" not in archive.namelist():
                    raise BackupError("invalid_backup", "Das Backup enthält unerwartete Dateien")
                manifest = json.loads(archive.read("manifest.json"))
                files = {name: archive.read(name) for name in archive.namelist() if name != "manifest.json"}
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
            raise BackupError("invalid_backup", "Der Backup-Inhalt ist ungültig") from exc
        if manifest.get("application") != "sim-admin" or manifest.get("format_version") != 1:
            raise BackupError("incompatible_backup", "Diese Backup-Version ist nicht kompatibel")
        for name, data in files.items():
            expected = manifest.get("contents", {}).get(name, {}).get("sha256")
            if expected != hashlib.sha256(data).hexdigest():
                raise BackupError("verification_failed", "Die Prüfsumme des Backups ist ungültig")
        return manifest, files

    def _build_payload(self, created_at: datetime) -> bytes:
        with tempfile.TemporaryDirectory() as temporary_directory:
            snapshot = Path(temporary_directory) / "audit.db"
            self._audit.snapshot(snapshot)
            database = snapshot.read_bytes()
            files = {"database/audit.db": database}
            if self._profiles:
                profile_db = Path(temporary_directory) / "profiles.db"; profile_key = Path(temporary_directory) / "profile.key"
                self._profiles.snapshot(profile_db, profile_key)
                files["database/profiles.db"] = profile_db.read_bytes(); files["config/profile.key"] = profile_key.read_bytes()
        manifest = {
            "application": "sim-admin",
            "format_version": 1,
            "created_at": created_at.isoformat(),
            "encryption": "AES-256-GCM",
            "contents": {name: {"sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()},
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            for name, data in files.items(): archive.writestr(name, data)
        return buffer.getvalue()
