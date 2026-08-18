"""SQLite-backed metadata-only audit trail."""

from datetime import UTC, datetime
import os
from pathlib import Path
import sqlite3
from threading import Lock

from app.models import AuditEvent

DEFAULT_AUDIT_DATABASE = "/opt/sim-admin/application/data/database/audit.db"


class AuditService:
    """Persist security-relevant actions without subscriber or secret data."""

    def __init__(self, database: str | None = None) -> None:
        self._database = database or os.getenv(
            "SIM_ADMIN_AUDIT_DB", DEFAULT_AUDIT_DATABASE
        )
        self._lock = Lock()
        if self._database != ":memory:":
            Path(self._database).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._database, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT
            )
            """
        )
        self._connection.commit()
        if self._database != ":memory:":
            os.chmod(self._database, 0o600)

    def record(
        self,
        action: str,
        status: str,
        detail: str | None = None,
        username: str = "admin",
    ) -> None:
        """Record only caller-supplied, non-sensitive metadata."""
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO audit_events (created_at, username, action, status, detail)
                VALUES (?, ?, ?, ?, ?)
                """,
                (datetime.now(UTC).isoformat(), username, action, status, detail),
            )
            self._connection.commit()

    def list_recent(self, limit: int = 100) -> list[AuditEvent]:
        safe_limit = min(max(limit, 1), 500)
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, created_at, username, action, status, detail
                FROM audit_events ORDER BY id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [AuditEvent.model_validate(dict(row)) for row in rows]

    def snapshot(self, destination: Path) -> None:
        """Create a transactionally consistent SQLite snapshot."""
        with self._lock:
            target = sqlite3.connect(destination)
            try:
                self._connection.backup(target)
            finally:
                target.close()

    def restore(self, source: Path) -> None:
        """Replace the active database contents from a validated snapshot."""
        with self._lock:
            origin = sqlite3.connect(source)
            try:
                origin.backup(self._connection)
                self._connection.commit()
            finally:
                origin.close()
