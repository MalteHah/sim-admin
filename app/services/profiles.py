"""Device-key encrypted local SIM profile vault."""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock

from app.models import ProfileChangeSummary, ProfileEditableView, ProfileImportResult, ProfileRevisionSummary, ProfileSummary, ProvisioningDraft, SuciKeySummary
from app.adapters.suci import normalize_hnet_public_key
from app.services.imports import CSVImportError, CSVImportPreviewService

AAD = b"sim-admin-profile-v1"
INVENTORY_AAD = b"sim-admin-inventory-v1"
SUCI_KEY_AAD = b"sim-admin-suci-key-v1"


def _optional_int(value: object) -> object | None:
    return None if value in (None, "") else value


def _revision_note(fields: list[str], prefix: str = "Geändert") -> str:
    labels = {"imsi": "IMSI", "msisdn": "MSISDN", "acc": "ACC", "ki": "Ki", "opc": "OPc",
        "impi": "IMPI", "impu": "IMPU", "ims_domain": "IMS-Domain", "ist": "IST",
        "routing_indicator": "Routing Indicator", "protection_scheme": "SUCI-Schutzverfahren",
        "hn_public_key_id": "HN-Key-ID", "hn_public_key": "HN-Schlüssel"}
    return f"{prefix}: {', '.join(labels.get(field, field) for field in fields)}"


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
            nonce BLOB NOT NULL, ciphertext BLOB NOT NULL, note TEXT NOT NULL DEFAULT 'Bestehende Revision',
            PRIMARY KEY (profile_id, revision),
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )""")
        revision_columns = {row[1] for row in self._connection.execute("PRAGMA table_info(profile_revisions)")}
        if "note" not in revision_columns:
            self._connection.execute("ALTER TABLE profile_revisions ADD COLUMN note TEXT NOT NULL DEFAULT 'Bestehende Revision'")
        self._connection.execute("""INSERT OR IGNORE INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext)
            SELECT id, revision, created_at, nonce, ciphertext FROM profiles""")
        self._connection.execute("""CREATE TABLE IF NOT EXISTS profile_change_drafts (
            profile_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, base_revision INTEGER NOT NULL,
            changed_fields TEXT NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )""")
        self._connection.execute("""CREATE TABLE IF NOT EXISTS profile_inventory (
            profile_id INTEGER PRIMARY KEY, updated_at TEXT NOT NULL,
            nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )""")
        self._connection.execute("""CREATE TABLE IF NOT EXISTS suci_keys (
            id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
            nonce BLOB NOT NULL, ciphertext BLOB NOT NULL
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
                self._connection.execute("INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext, note) VALUES (?, 1, ?, ?, ?, ?)", (cursor.lastrowid, created_at, nonce, ciphertext, "Ersterfassung per CSV-Import"))
            self._connection.commit()
        return ProfileImportResult(imported=len(records))

    def add_profile(self, draft: ProvisioningDraft, card_verified: bool = False) -> ProfileSummary:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        record = {"iccid": draft.iccid, "imsi": draft.imsi, "msisdn": draft.msisdn or "", "acc": draft.acc.upper(),
            "ki": draft.ki.get_secret_value().upper(), "opc": draft.opc.get_secret_value().upper(), "adm": draft.adm.get_secret_value(),
            "impi": draft.impi or "", "impu": draft.impu or "", "ims_domain": draft.ims_domain or "", "ist": (draft.ist or "").upper()}
        record.update({"routing_indicator": draft.routing_indicator or "", "protection_scheme": draft.protection_scheme,
            "hn_public_key_id": draft.hn_public_key_id, "hn_public_key": (draft.hn_public_key or "").upper()})
        with self._lock:
            if any(item.iccid == draft.iccid for item in self._list_unlocked()): raise ValueError("duplicate_iccid")
            created_at = datetime.now(UTC).isoformat(); nonce = os.urandom(12)
            ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(record, separators=(",", ":")).encode(), AAD)
            cursor = self._connection.execute("INSERT INTO profiles (created_at, nonce, ciphertext, revision, card_verified) VALUES (?, ?, ?, 1, ?)", (created_at, nonce, ciphertext, int(card_verified)))
            self._connection.execute("INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext, note) VALUES (?, 1, ?, ?, ?, ?)", (cursor.lastrowid, created_at, nonce, ciphertext, "Ersterfassung einer Einzelkarte"))
            self._connection.commit(); profile_id = int(cursor.lastrowid)
        return ProfileSummary(id=profile_id, created_at=created_at, iccid=draft.iccid, imsi=draft.imsi,
            ki_configured=True, opc_configured=True, adm_configured=True, revision=1, card_verified=card_verified,
            ims_configured=bool(draft.impi or draft.impu or draft.ims_domain or draft.ist),
            fivegs_configured=bool(draft.routing_indicator or draft.protection_scheme is not None or draft.hn_public_key_id is not None or draft.hn_public_key))

    def find_by_iccid(self, iccid: str) -> ProfileSummary | None:
        return next((profile for profile in self.list_profiles() if profile.iccid == iccid), None)

    def mark_card_verified(self, profile_id: int) -> None:
        with self._lock:
            cursor = self._connection.execute("UPDATE profiles SET card_verified = 1 WHERE id = ?", (profile_id,))
            if cursor.rowcount == 0: raise KeyError(profile_id)
            self._connection.commit()

    def adopt_card_imsi(self, profile_id: int, card_iccid: str, card_imsi: str) -> int:
        """Adopt a securely re-read card IMSI as a new encrypted profile revision."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with self._lock:
            row = self._connection.execute(
                "SELECT revision, nonce, ciphertext FROM profiles WHERE id = ?", (profile_id,)
            ).fetchone()
            if row is None:
                raise KeyError(profile_id)
            if self._connection.execute(
                "SELECT 1 FROM profile_change_drafts WHERE profile_id = ?", (profile_id,)
            ).fetchone() is not None:
                raise ValueError("pending_change")
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], AAD))
            if record["iccid"] != card_iccid:
                raise ValueError("iccid_mismatch")
            if record["imsi"] == card_imsi:
                raise ValueError("no_changes")
            updated = dict(record)
            updated["imsi"] = card_imsi
            ProvisioningDraft(
                iccid=updated["iccid"], imsi=updated["imsi"], msisdn=updated.get("msisdn") or None,
                acc=updated.get("acc") or "0001", ki=updated["ki"], opc=updated["opc"], adm=updated["adm"],
            )
            created_at = datetime.now(UTC).isoformat()
            nonce = os.urandom(12)
            ciphertext = AESGCM(self._key).encrypt(
                nonce, json.dumps(updated, separators=(",", ":")).encode(), AAD
            )
            revision = int(row["revision"]) + 1
            self._connection.execute(
                "UPDATE profiles SET created_at = ?, nonce = ?, ciphertext = ?, revision = ?, card_verified = 1 WHERE id = ?",
                (created_at, nonce, ciphertext, revision, profile_id),
            )
            self._connection.execute(
                "INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext, note) VALUES (?, ?, ?, ?, ?, ?)",
                (profile_id, revision, created_at, nonce, ciphertext, "IMSI von Karte übernommen"),
            )
            self._connection.commit()
        return revision

    def adopt_readable_card_fields(self, profile_id: int, card_iccid: str, values: dict, fields: list[str]) -> tuple[int, list[str]]:
        """Commit selected, re-read non-secret IMS/SUCI values as a revision."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        allowed = {"impi", "impu", "ims_domain", "ist", "suci"}
        selected = set(fields)
        if not selected or not selected <= allowed: raise ValueError("unsupported_fields")
        with self._lock:
            row = self._connection.execute("SELECT revision, nonce, ciphertext FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if row is None: raise KeyError(profile_id)
            if self._connection.execute("SELECT 1 FROM profile_change_drafts WHERE profile_id = ?", (profile_id,)).fetchone() is not None:
                raise ValueError("pending_change")
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], AAD))
            if record["iccid"] != card_iccid: raise ValueError("iccid_mismatch")
            updated = dict(record); adopted: list[str] = []
            for field in ("impi", "impu", "ims_domain", "ist"):
                if field in selected and (record.get(field) or None) != (values.get(field) or None):
                    updated[field] = values.get(field) or ""; adopted.append(field)
            if "suci" in selected:
                suci_fields = ("routing_indicator", "protection_scheme", "hn_public_key_id", "hn_public_key")
                if any(record.get(field) != values.get(field) for field in suci_fields):
                    for field in suci_fields: updated[field] = values.get(field)
                    adopted.extend(suci_fields)
            if not adopted: raise ValueError("no_changes")
            ProvisioningDraft(iccid=updated["iccid"], imsi=updated["imsi"], msisdn=updated.get("msisdn") or None,
                acc=updated.get("acc") or "0001", ki=updated["ki"], opc=updated["opc"], adm=updated["adm"],
                impi=updated.get("impi") or None, impu=updated.get("impu") or None, ims_domain=updated.get("ims_domain") or None,
                ist=updated.get("ist") or None, routing_indicator=updated.get("routing_indicator") or None,
                protection_scheme=_optional_int(updated.get("protection_scheme")), hn_public_key_id=_optional_int(updated.get("hn_public_key_id")),
                hn_public_key=updated.get("hn_public_key") or None)
            created_at = datetime.now(UTC).isoformat(); nonce = os.urandom(12)
            ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(updated, separators=(",", ":")).encode(), AAD)
            revision = int(row["revision"]) + 1
            self._connection.execute("UPDATE profiles SET created_at = ?, nonce = ?, ciphertext = ?, revision = ?, card_verified = 1 WHERE id = ?",
                (created_at, nonce, ciphertext, revision, profile_id))
            self._connection.execute("INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext, note) VALUES (?, ?, ?, ?, ?, ?)",
                (profile_id, revision, created_at, nonce, ciphertext, _revision_note(adopted, "Von Karte übernommen")))
            self._connection.commit()
        return revision, adopted

    def delete_profile(self, profile_id: int, confirmation_iccid: str) -> None:
        record = self._get_record(profile_id)
        if record["iccid"] != confirmation_iccid: raise ValueError("iccid_mismatch")
        with self._lock:
            self._connection.execute("DELETE FROM profile_inventory WHERE profile_id = ?", (profile_id,))
            self._connection.execute("DELETE FROM profile_change_drafts WHERE profile_id = ?", (profile_id,))
            self._connection.execute("DELETE FROM profile_revisions WHERE profile_id = ?", (profile_id,))
            cursor = self._connection.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            if cursor.rowcount == 0: raise KeyError(profile_id)
            self._connection.commit()

    def list_profiles(self) -> list[ProfileSummary]:
        with self._lock: return self._list_unlocked()

    def set_inventory(self, profile_id: int, status: str, issued_to: str | None, issued_at: str | None, note: str | None) -> None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        record = {"status": status, "issued_to": issued_to or "", "issued_at": issued_at or "", "note": note or ""}
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(record, separators=(",", ":")).encode(), INVENTORY_AAD)
        updated_at = datetime.now(UTC).isoformat()
        with self._lock:
            if self._connection.execute("SELECT 1 FROM profiles WHERE id = ?", (profile_id,)).fetchone() is None:
                raise KeyError(profile_id)
            self._connection.execute("""INSERT INTO profile_inventory (profile_id, updated_at, nonce, ciphertext)
                VALUES (?, ?, ?, ?) ON CONFLICT(profile_id) DO UPDATE SET updated_at=excluded.updated_at,
                nonce=excluded.nonce, ciphertext=excluded.ciphertext""", (profile_id, updated_at, nonce, ciphertext))
            self._connection.commit()

    def import_suci_key(self, name: str, scheme: int, key_id: int, key_data: str) -> SuciKeySummary:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        public_key, fingerprint = normalize_hnet_public_key(scheme, key_data)
        with self._lock:
            existing = self._list_suci_keys_unlocked()
            if any(item.scheme == scheme and item.key_id == key_id for item in existing):
                raise ValueError("duplicate_key_id")
            if any(item.fingerprint == fingerprint for item in existing):
                raise ValueError("duplicate_key")
            created_at = datetime.now(UTC).isoformat()
            record = {"name": name.strip(), "scheme": scheme, "key_id": key_id,
                "public_key": public_key, "fingerprint": fingerprint, "active": True}
            nonce = os.urandom(12)
            ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(record, separators=(",", ":")).encode(), SUCI_KEY_AAD)
            cursor = self._connection.execute("INSERT INTO suci_keys (created_at, nonce, ciphertext) VALUES (?, ?, ?)",
                (created_at, nonce, ciphertext))
            self._connection.commit()
            key_db_id = int(cursor.lastrowid)
        return SuciKeySummary(id=key_db_id, created_at=created_at, in_use=False, **record)

    def list_suci_keys(self) -> list[SuciKeySummary]:
        with self._lock:
            return self._list_suci_keys_unlocked()

    def set_suci_key_active(self, key_db_id: int, active: bool) -> SuciKeySummary:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with self._lock:
            row = self._connection.execute("SELECT created_at, nonce, ciphertext FROM suci_keys WHERE id = ?", (key_db_id,)).fetchone()
            if row is None: raise KeyError(key_db_id)
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], SUCI_KEY_AAD))
            record["active"] = active
            nonce = os.urandom(12)
            ciphertext = AESGCM(self._key).encrypt(nonce, json.dumps(record, separators=(",", ":")).encode(), SUCI_KEY_AAD)
            self._connection.execute("UPDATE suci_keys SET nonce = ?, ciphertext = ? WHERE id = ?", (nonce, ciphertext, key_db_id))
            self._connection.commit()
            in_use = self._suci_key_in_use_unlocked(record)
        return SuciKeySummary(id=key_db_id, created_at=row["created_at"], in_use=in_use, **record)

    def delete_suci_key(self, key_db_id: int) -> None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with self._lock:
            row = self._connection.execute("SELECT nonce, ciphertext FROM suci_keys WHERE id = ?", (key_db_id,)).fetchone()
            if row is None: raise KeyError(key_db_id)
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], SUCI_KEY_AAD))
            if self._suci_key_in_use_unlocked(record): raise ValueError("key_in_use")
            self._connection.execute("DELETE FROM suci_keys WHERE id = ?", (key_db_id,))
            self._connection.commit()

    def _list_suci_keys_unlocked(self) -> list[SuciKeySummary]:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        result = []
        for row in self._connection.execute("SELECT id, created_at, nonce, ciphertext FROM suci_keys ORDER BY id"):
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], SUCI_KEY_AAD))
            result.append(SuciKeySummary(id=row["id"], created_at=row["created_at"],
                in_use=self._suci_key_in_use_unlocked(record), **record))
        return result

    def _suci_key_in_use_unlocked(self, key_record: dict) -> bool:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        queries = (
            "SELECT nonce, ciphertext FROM profile_revisions",
            "SELECT nonce, ciphertext FROM profile_change_drafts",
        )
        for query in queries:
            for row in self._connection.execute(query):
                record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], AAD))
                if (record.get("protection_scheme") == key_record["scheme"]
                    and record.get("hn_public_key_id") == key_record["key_id"]
                    and (record.get("hn_public_key") or "").upper() == key_record["public_key"]):
                    return True
        return False

    def list_revisions(self, profile_id: int) -> list[ProfileRevisionSummary]:
        with self._lock:
            exists = self._connection.execute("SELECT 1 FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if exists is None: raise KeyError(profile_id)
            rows = self._connection.execute("SELECT revision, created_at, note FROM profile_revisions WHERE profile_id = ? ORDER BY revision DESC", (profile_id,)).fetchall()
        return [ProfileRevisionSummary(revision=row["revision"], created_at=row["created_at"], note=row["note"]) for row in rows]

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
        return ProfileEditableView(iccid=record["iccid"], imsi=record["imsi"], msisdn=record.get("msisdn") or None, acc=record.get("acc") or "0001", revision=row["revision"], pending_change=pending is not None, changed_fields=changed_fields,
            impi=record.get("impi") or None, impu=record.get("impu") or None, ims_domain=record.get("ims_domain") or None, ist=record.get("ist") or None,
            routing_indicator=record.get("routing_indicator") or None, protection_scheme=_optional_int(record.get("protection_scheme")),
            hn_public_key_id=_optional_int(record.get("hn_public_key_id")), hn_public_key=record.get("hn_public_key") or None)

    def prepare_change(self, profile_id: int, imsi: str, msisdn: str | None, acc: str, ki: str | None, opc: str | None,
        impi: str | None = None, impu: str | None = None, ims_domain: str | None = None, ist: str | None = None,
        routing_indicator: str | None = None, protection_scheme: int | None = None,
        hn_public_key_id: int | None = None, hn_public_key: str | None = None) -> ProfileChangeSummary:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        current = self._get_record(profile_id)
        updated = dict(current)
        proposed = {"imsi": imsi, "msisdn": msisdn or "", "acc": acc.upper(), "impi": impi or "", "impu": impu or "", "ims_domain": ims_domain or "", "ist": (ist or "").upper()}
        proposed.update({"routing_indicator": routing_indicator or "", "protection_scheme": protection_scheme if protection_scheme is not None else "",
            "hn_public_key_id": hn_public_key_id if hn_public_key_id is not None else "", "hn_public_key": (hn_public_key or "").upper()})
        if ki: proposed["ki"] = ki.upper()
        if opc: proposed["opc"] = opc.upper()
        updated.update(proposed)
        ProvisioningDraft(iccid=current["iccid"], imsi=updated["imsi"], msisdn=updated["msisdn"] or None, acc=updated["acc"], ki=updated["ki"], opc=updated["opc"], adm=current["adm"],
            impi=updated.get("impi") or None, impu=updated.get("impu") or None, ims_domain=updated.get("ims_domain") or None, ist=updated.get("ist") or None,
            routing_indicator=updated.get("routing_indicator") or None, protection_scheme=_optional_int(updated.get("protection_scheme")),
            hn_public_key_id=_optional_int(updated.get("hn_public_key_id")), hn_public_key=updated.get("hn_public_key") or None)
        changed = sorted(
            field for field, value in proposed.items()
            if value != (current.get(field) if current.get(field) is not None else "")
        )
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
            acc=record.get("acc") or "0001", ki=record["ki"], opc=record["opc"], adm=record["adm"], impi=record.get("impi") or None,
            impu=record.get("impu") or None, ims_domain=record.get("ims_domain") or None, ist=record.get("ist") or None,
            routing_indicator=record.get("routing_indicator") or None, protection_scheme=_optional_int(record.get("protection_scheme")),
            hn_public_key_id=_optional_int(record.get("hn_public_key_id")), hn_public_key=record.get("hn_public_key") or None)

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
            row = self._connection.execute("SELECT base_revision, changed_fields, nonce, ciphertext FROM profile_change_drafts WHERE profile_id = ?", (profile_id,)).fetchone()
            active = self._connection.execute("SELECT revision FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if row is None or active is None: raise KeyError(profile_id)
            if row["base_revision"] != expected_base_revision or active["revision"] != expected_base_revision: raise ValueError("revision_conflict")
            revision = expected_base_revision + 1
            self._connection.execute("UPDATE profiles SET created_at = ?, nonce = ?, ciphertext = ?, revision = ?, card_verified = 1 WHERE id = ?", (created_at, row["nonce"], row["ciphertext"], revision, profile_id))
            fields = json.loads(row["changed_fields"])
            self._connection.execute("INSERT INTO profile_revisions (profile_id, revision, created_at, nonce, ciphertext, note) VALUES (?, ?, ?, ?, ?, ?)",
                (profile_id, revision, created_at, row["nonce"], row["ciphertext"], _revision_note(fields)))
            self._connection.execute("DELETE FROM profile_change_drafts WHERE profile_id = ?", (profile_id,))
            self._connection.commit()
        return revision

    def get_draft(self, profile_id: int) -> ProvisioningDraft:
        record = self._get_record(profile_id)
        return ProvisioningDraft(iccid=record["iccid"], imsi=record["imsi"], msisdn=record.get("msisdn") or None,
            acc=record.get("acc") or "0001", ki=record["ki"], opc=record["opc"], adm=record["adm"], impi=record.get("impi") or None,
            impu=record.get("impu") or None, ims_domain=record.get("ims_domain") or None, ist=record.get("ist") or None,
            routing_indicator=record.get("routing_indicator") or None, protection_scheme=_optional_int(record.get("protection_scheme")),
            hn_public_key_id=_optional_int(record.get("hn_public_key_id")), hn_public_key=record.get("hn_public_key") or None)

    def get_secrets(self, profile_id: int) -> dict[str, str]:
        record = self._get_record(profile_id)
        public = {"iccid", "imsi", "msisdn", "acc", "impi", "impu", "ims_domain", "ist", "routing_indicator", "protection_scheme", "hn_public_key_id", "hn_public_key"}
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
                profiles.revision, profiles.card_verified, profile_change_drafts.profile_id IS NOT NULL AS pending_change,
                profile_inventory.nonce AS inventory_nonce, profile_inventory.ciphertext AS inventory_ciphertext
                FROM profiles LEFT JOIN profile_change_drafts ON profile_change_drafts.profile_id = profiles.id
                LEFT JOIN profile_inventory ON profile_inventory.profile_id = profiles.id
                ORDER BY profiles.id DESC"""):
            record = json.loads(AESGCM(self._key).decrypt(row["nonce"], row["ciphertext"], AAD))
            inventory = {"status": "in_stock", "issued_to": "", "issued_at": "", "note": ""}
            if row["inventory_nonce"] is not None:
                inventory = json.loads(AESGCM(self._key).decrypt(row["inventory_nonce"], row["inventory_ciphertext"], INVENTORY_AAD))
            result.append(ProfileSummary(id=row["id"], created_at=row["created_at"], iccid=record["iccid"], imsi=record["imsi"], ki_configured=bool(record["ki"]), opc_configured=bool(record["opc"]), adm_configured=bool(record["adm"]), revision=row["revision"], pending_change=bool(row["pending_change"]), card_verified=bool(row["card_verified"]), ims_configured=bool(record.get("impi") or record.get("impu") or record.get("ims_domain") or record.get("ist")), fivegs_configured=bool(record.get("routing_indicator") or record.get("protection_scheme") is not None or record.get("hn_public_key_id") is not None or record.get("hn_public_key")), inventory_status=inventory.get("status", "in_stock"), issued_to=inventory.get("issued_to") or None, issued_at=inventory.get("issued_at") or None, inventory_note=inventory.get("note") or None))
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
