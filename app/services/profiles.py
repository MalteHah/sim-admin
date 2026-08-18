"""Device-key encrypted local SIM profile vault."""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock

from app.models import ProfileChangeSummary, ProfileEditableView, ProfileImportResult, ProfileRevisionSummary, ProfileSummary, ProvisioningDraft
from app.services.imports import CSVImportError, CSVImportPreviewService

AAD = b"sim-admin-profile-v1"


class ProfileVaultService:
    def __init__(self, database: str | None = None, key_file: str | None = None) -> None:
        self._database = database or os.getenv("SIM_ADMIN_PROFILE_DB", "/opt/sim-admin/application/data/database/profiles.db")
        self._key_file = Path(key_file or os.getenv("SIM_ADMIN_PROFILE_KEY", "/opt/sim-admin/application/config/profile.key"))
        self._lock = Lock()
        if self._database != ":memory:":
            Path(self._database).parent.mkdir(parents=True, exist_ok=True)
        self._key = self._load_or_create_key()
        self._connection = sqlite3.connect(self._database, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL)")
        columns = {row[1] for row in self._connection.execute("PRAGMA table_info(profiles)")}
        if "revision" not in columns:
            self._connection.execute("ALTER TABLE profiles ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
        if "card_verified" not in columns:
            self._connection.execute("ALTER TABLE profiles ADD COLUMN card_verified INTEGER NOT NULL DEFAULT 0")
            self._connection.execute("UPDATE profiles SET card_verified = 1 WHERE revision > 1")
        self._connection.execute("""CREATE TABLE IF NOT EXISTS profile_revisions (
            profile_id INTEGER NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL,
            nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
            PRIMARY KEY (profile_id, revision),
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )""")
        self._connection.execute("""INSERT OR IGNORE INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext)
            SELECT id, revision, created_at, nonce, ciphertext FROM profiles""")
        self._connection.execute("""CREATE TABLE IF NOT EXISTS profile_change_drafts (
            profile_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, base_revision INTEGER NOT NULL,
            changed_fields TEXT NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )""")
        self._connection.commit()
        if self._database != ":memory:": os.chmod(self._database, 0o600)

    def _load_or_create_key(self) -> bytes:
        self._key_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._key_file.exists():
            temporary = self._key_file.with_suffix(".tmp")
            with temporary.open("xb") as handle: handle.write(os.urandom(32))
            os.chmod(temporary, 0o600); temporary.replace(self._key_file)
        os.chmod(self._key_file, 0o600)
        key = self._key_file.read_bytes()
        if len(key) != 32: raise RuntimeError("invalid profile vault key")
        return key

    def import_csv(self, content: str) -> ProfileImportResult:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        preview, records = CSVImportPreviewService().parse(content)
        if preview.invalid_rows:
            raise CSVImportError("validation_errors", "Nur eine vollständig gültige Datei kann gespeichert werden")
        with self._lock:
            existing = {(item.iccid, item.imsi) for item in self._list_unlocked()}
            if any((record["iccid"], record["imsi"]) in existing for record in records):
                raise CSVImportError("duplicate_profile", "Mindestens ein Profil ist bereits im Tresor vorhanden")
            for record in records:
                nonce = os.urandom(12)
                ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(record, separators=(",", ":")).encode(), AAD)
                created_at = datetime.now(UTC).isoformat()
                cursor = self._connection.execute("INSERT INTO profiles (created_at, nonce, ciphertext, revision) VALUES (?, ?, ?, 1)", (created_at, nonce, ciphertext))
                self._connection.execute("INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext) VALUES (?, 1, ?, ?, ?)", (cursor.lastrowid, created_at, nonce, ciphertext))
            self._connection.commit()
        return ProfileImportResult(imported=len(records))

    def add_profile(self, draft: ProvisioningDraft, card_verified: bool = False) -> ProfileSummary:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        record = {"iccid": draft.iccid, "imsi": draft.imsi, "msisdn": draft.msisdn or "", "acc": draft.acc.upper(),
            "ki": draft.ki.get_secret_value().upper(), "opc": draft.opc.get_secret_value().upper(), "adm": draft.adm.get_secret_value()}
        with self._lock:
            if any(item.iccid == draft.iccid for item in self._list_unlocked()): raise ValueError("duplicate_iccid")
            created_at = datetime.now(UTC).isoformat(); nonce = os.urandom(12)
            ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(record, separators=(",", ":")).encode(), AAD)
            cursor = self._connection.execute("INSERT INTO profiles (created_at, nonce, ciphertext, revision, card_verified) VALUES (?, ?, ?, 1, ?)", (created_at, nonce, ciphertext, int(card_verified)))
            self._connection.execute("INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext) VALUES (?, 1, ?, ?, ?)", (cursor.lastrowid, created_at, nonce, ciphertext))
            self._connection.commit(); profile_id = int(cursor.lastrowid)
        return ProfileSummary(id=profile_id, created_at=created_at, iccid=draft.iccid, imsi=draft.imsi,
            ki_configured=True, opc_configured=True, adm_configured=True, revision=1, card_verified=card_verified)

    def find_by_iccid(self, iccid: str) -> ProfileSummary | None:
        return next((profile for profile in self.list_profiles() if profile.iccid == iccid), None)

    def mark_card_verified(self, profile_id: int) -> None:
        with self._lock:
            cursor = self._connection.execute("UPDATE profiles SET card_verified = 1 WHERE id = ?", (profile_id,))
            if cursor.rowcount == 0: raise KeyError(profile_id)
            self._connection.commit()

    def delete_profile(self, profile_id: int, confirmation_iccid: str) -> None:
        record = self._get_record(profile_id)
        if record["iccid"] != confirmation_iccid: raise ValueError("iccid_mismatch")
        with self._lock:
            self._connection.execute("DELETE FROM profile_change_drafts WHERE profile_id = ?", (profile_id,))
            self._connection.execute("DELETE FROM profile_revisions WHERE profile_id = ?", (profile_id,))
            cursor = self._connection.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            if cursor.rowcount == 0: raise KeyError(profile_id)
            self._connection.commit()

    def list_profiles(self) -> list[ProfileSummary]:
        with self._lock: return self._list_unlocked()

    def list_revisions(self, profile_id: int) -> list[ProfileRevisionSummary]:
        with self._lock:
            exists = self._connection.execute("SELECT 1 FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if exists is None: raise KeyError(profile_id)
            rows = self._connection.execute("SELECT revision, created_at FROM profile_revisions WHERE profile_id = ? ORDER BY revision DESC", (profile_id,)).fetchall()
        return [ProfileRevisionSummary(revision=row["revision"], created_at=row["created_at"]) for row in rows]

    def get_editable(self, profile_id: int) -> ProfileEditableView:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        record = self._get_record(profile_id)
        with self._lock:
            row = self._connection.execute("SELECT revision FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            pending = self._connection.execute("SELECT changed_fields, nonce, ciphertext FROM profile_change_drafts WHERE profile_id = ?", (profile_id,)).fetchone()
        changed_fields: list[str] = []
        if pending is not None:
            record = json.loads(AESGCM(self._key).decrypt(pending["nonce"], pending["ciphertext"], AAD))
            changed_fields = json.loads(pending["changed_fields"])
        return ProfileEditableView(iccid=record["iccid"], imsi=record["imsi"], msisdn=record.get("msisdn") or None, acc=record.get("acc") or "0001", revision=row["revision"], pending_change=pending is not None, changed_fields=changed_fields)

    def prepare_change(self, profile_id: int, imsi: str, msisdn: str | None, acc: str, ki: str | None, opc: str | None) -> ProfileChangeSummary:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        current = self._get_record(profile_id)
        updated = dict(current)
        proposed = {"imsi": imsi, "msisdn": msisdn or "", "acc": acc.upper()}
        if ki: proposed["ki"] = ki.upper()
        if opc: proposed["opc"] = opc.upper()
        updated.update(proposed)
        ProvisioningDraft(iccid=current["iccid"], imsi=updated["imsi"], msisdn=updated["msisdn"] or None, acc=updated["acc"], ki=updated["ki"], opc=updated["opc"], adm=current["adm"])
        changed = sorted(field for field, value in proposed.items() if value != current.get(field, ""))
        if not changed: raise ValueError("no_changes")
        created_at = datetime.now(UTC).isoformat(); nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(updated, separators=(",", ":")).encode(), AAD)
        with self._lock:
            row = self._connection.execute("SELECT revision FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            self._connection.execute("""INSERT INTO profile_change_drafts (profile_id, created_at, base_revision, changed_fields, nonce, ciphertext)
                VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(profile_id) DO UPDATE SET created_at=excluded.created_at,
                base_revision=excluded.base_revision, changed_fields=excluded.changed_fields, nonce=excluded.nonce, ciphertext=excluded.ciphertext""",
                (profile_id, created_at, row["revision"], json.dumps(changed), nonce, ciphertext))
            self._connection.commit()
        return ProfileChangeSummary(profile_id=profile_id, created_at=created_at, base_revision=row["revision"], changed_fields=changed)

    def get_change_summary(self, profile_id: int) -> ProfileChangeSummary | None:
        with self._lock:
            row = self._connection.execute("SELECT created_at, base_revision, changed_fields FROM profile_change_drafts WHERE profile_id = ?", (profile_id,)).fetchone()
        if row is None: return None
        return ProfileChangeSummary(profile_id=profile_id, created_at=row["created_at"], base_revision=row["base_revision"], changed_fields=json.loads(row["changed_fields"]))

    def get_change_draft(self, profile_id: int) -> ProvisioningDraft:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with self._lock:
            row = self._connection.execute("SELECT nonce, ciphertext FROM profile_change_drafts WHERE profile_id = ?", (profile_id,)).fetchone()
        if row is None: raise KeyError(profile_id)
        record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], AAD))
        return ProvisioningDraft(iccid=record["iccid"], imsi=record["imsi"], msisdn=record.get("msisdn") or None,
            acc=record.get("acc") or "0001", ki=record["ki"], opc=record["opc"], adm=record["adm"])

    def discard_change(self, profile_id: int) -> bool:
        with self._lock:
            exists = self._connection.execute("SELECT 1 FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if exists is None: raise KeyError(profile_id)
            cursor = self._connection.execute("DELETE FROM profile_change_drafts WHERE profile_id = ?", (profile_id,))
            self._connection.commit()
        return cursor.rowcount > 0

    def commit_change(self, profile_id: int, expected_base_revision: int) -> int:
        created_at = datetime.now(UTC).isoformat()
        with self._lock:
            row = self._connection.execute("SELECT base_revision, nonce, ciphertext FROM profile_change_drafts WHERE profile_id = ?", (profile_id,)).fetchone()
            active = self._connection.execute("SELECT revision FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if row is None or active is None: raise KeyError(profile_id)
            if row["base_revision"] != expected_base_revision or active["revision"] != expected_base_revision: raise ValueError("revision_conflict")
            revision = expected_base_revision + 1
            self._connection.execute("UPDATE profiles SET created_at = ?, nonce = ?, ciphertext = ?, revision = ?, card_verified = 1 WHERE id = ?", (created_at, row["nonce"], row["ciphertext"], revision, profile_id))
            self._connection.execute("INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext) VALUES (?, ?, ?, ?, ?)", (profile_id, revision, created_at, row["nonce"], row["ciphertext"]))
            self._connection.execute("DELETE FROM profile_change_drafts WHERE profile_id = ?", (profile_id,))
            self._connection.commit()
        return revision

    def get_draft(self, profile_id: int) -> ProvisioningDraft:
        record = self._get_record(profile_id)
        return ProvisioningDraft(iccid=record["iccid"], imsi=record["imsi"], msisdn=record.get("msisdn") or None,
            acc=record.get("acc") or "0001", ki=record["ki"], opc=record["opc"], adm=record["adm"])

    def get_secrets(self, profile_id: int) -> dict[str, str]:
        record = self._get_record(profile_id)
        public = {"iccid", "imsi", "msisdn", "acc"}
        secrets: dict[str, str] = {}
        for key, value in record.items():
            if key in public or not value:
                continue
            label = "ADM1" if key in {"adm", "adm1"} else key.upper()
            secrets[label] = value
        return secrets

    def _get_record(self, profile_id: int) -> dict[str, str]:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with self._lock:
            row = self._connection.execute("SELECT nonce, ciphertext FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if row is None: raise KeyError(profile_id)
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], AAD))
        return record

    def _list_unlocked(self) -> list[ProfileSummary]:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        result = []
        for row in self._connection.execute("""SELECT profiles.id, profiles.created_at, profiles.nonce, profiles.ciphertext,
                profiles.revision, profiles.card_verified, profile_change_drafts.profile_id IS NOT NULL AS pending_change
                FROM profiles LEFT JOIN profile_change_drafts ON profile_change_drafts.profile_id = profiles.id
                ORDER BY profiles.id DESC"""):
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], AAD))
            result.append(ProfileSummary(id=row["id"], created_at=row["created_at"], iccid=record["iccid"], imsi=record["imsi"], ki_configured=bool(record["ki"]), opc_configured=bool(record["opc"]), adm_configured=bool(record["adm"]), revision=row["revision"], pending_change=bool(row["pending_change"]), card_verified=bool(row["card_verified"])))
        return result

    def snapshot(self, database: Path, key_file: Path) -> None:
        with self._lock:
            target = sqlite3.connect(database)
            try: self._connection.backup(target)
            finally: target.close()
            key_file.write_bytes(self._key)

    def restore(self, database: Path, key_file: Path) -> None:
        key = key_file.read_bytes()
        if len(key) != 32: raise ValueError("invalid profile key")
        with self._lock:
            source = sqlite3.connect(database)
            try: source.backup(self._connection); self._connection.commit()
            finally: source.close()
            self._key_file.write_bytes(key); os.chmod(self._key_file, 0o600); self._key = key
