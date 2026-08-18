"""Small, dependency-free authentication service for the standalone UI."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import time


def _b64encode(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class AuthSettings:
    """Authentication configuration loaded from the service environment."""

    username: str
    password_hash: str | None
    session_secret: bytes
    credential_file: Path | None = None
    session_seconds: int = 8 * 60 * 60
    secure_cookie: bool = False

    @classmethod
    def from_environment(cls) -> "AuthSettings":
        username = os.getenv("SIM_ADMIN_USERNAME")
        password_hash = os.getenv("SIM_ADMIN_PASSWORD_HASH")
        session_secret = os.getenv("SIM_ADMIN_SESSION_SECRET")
        credential_file = os.getenv("SIM_ADMIN_CREDENTIAL_FILE")
        if not username or not session_secret or not (password_hash or credential_file):
            raise RuntimeError("SIM-Admin authentication is not configured")
        return cls(
            username,
            password_hash,
            session_secret.encode("utf-8"),
            Path(credential_file) if credential_file else None,
            secure_cookie=os.getenv("SIM_ADMIN_SECURE_COOKIE", "false").lower()
            in {"1", "true", "yes"},
        )


class PasswordChangeError(RuntimeError):
    """A safe password-change error suitable for presentation to the user."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AuthService:
    """Verify credentials and issue signed, expiring session cookies."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    @property
    def username(self) -> str:
        return self._settings.username

    @property
    def secure_cookie(self) -> bool:
        return self._settings.secure_cookie

    def verify_login(self, username: str, password: str, client: str) -> bool:
        now = time.time()
        attempts = self._failures[client]
        while attempts and attempts[0] < now - 300:
            attempts.popleft()
        if len(attempts) >= 5:
            return False

        valid = hmac.compare_digest(username, self._settings.username)
        valid = self._verify_password(password) and valid
        if valid:
            attempts.clear()
            return True
        attempts.append(now)
        return False

    def change_password(self, current: str, new: str, client: str) -> None:
        if not self.verify_login(self._settings.username, current, client):
            raise PasswordChangeError("invalid_password", "Aktuelles Passwort ist falsch")
        if len(new) < 12:
            raise PasswordChangeError(
                "weak_password", "Das neue Passwort muss mindestens 12 Zeichen haben"
            )
        if hmac.compare_digest(current, new):
            raise PasswordChangeError(
                "unchanged_password", "Das neue Passwort muss sich unterscheiden"
            )
        if self._settings.credential_file is None:
            raise PasswordChangeError(
                "storage_unavailable", "Passwortspeicher ist nicht konfiguriert"
            )

        salt = secrets.token_bytes(16)
        password_hash = hashlib.scrypt(
            new.encode("utf-8"), salt=salt, n=2**14, r=8, p=1
        ).hex()
        self._write_password_hash(f"{salt.hex()}:{password_hash}")

    def create_session(self) -> str:
        payload = json.dumps(
            {
                "sub": self._settings.username,
                "exp": int(time.time()) + self._settings.session_seconds,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        encoded = _b64encode(payload)
        signature = hmac.new(
            self._settings.session_secret,
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{encoded}.{_b64encode(signature)}"

    def verify_session(self, token: str | None) -> bool:
        if not token:
            return False
        try:
            encoded, supplied_signature = token.split(".", 1)
            expected_signature = hmac.new(
                self._settings.session_secret,
                encoded.encode("ascii"),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(
                expected_signature, _b64decode(supplied_signature)
            ):
                return False
            payload = json.loads(_b64decode(encoded))
            return (
                payload.get("sub") == self._settings.username
                and int(payload.get("exp", 0)) >= int(time.time())
            )
        except (ValueError, TypeError, json.JSONDecodeError):
            return False

    def _verify_password(self, password: str) -> bool:
        try:
            salt_hex, expected_hex = self._read_password_hash().split(":", 1)
            calculated = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=2**14,
                r=8,
                p=1,
            )
            return hmac.compare_digest(calculated.hex(), expected_hex)
        except (ValueError, TypeError):
            return False

    def _read_password_hash(self) -> str:
        if (
            self._settings.credential_file is not None
            and self._settings.credential_file.exists()
        ):
            payload = json.loads(
                self._settings.credential_file.read_text(encoding="utf-8")
            )
            return str(payload["password_hash"])
        if self._settings.password_hash is None:
            raise ValueError("Password hash is unavailable")
        return self._settings.password_hash

    def _write_password_hash(self, password_hash: str) -> None:
        target = self._settings.credential_file
        if target is None:
            raise ValueError("Credential file is unavailable")
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=".auth-")
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump({"password_hash": password_hash}, handle)
                handle.write("\n")
            os.replace(temporary_name, target)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
