"""Focused tests for password storage and changes."""

import json

from app.core.auth import AuthService, AuthSettings, PasswordChangeError


def test_password_change_updates_hash_file(tmp_path) -> None:
    credential_file = tmp_path / "auth.json"
    credential_file.write_text(
        json.dumps({"password_hash": __import__("os").environ["SIM_ADMIN_PASSWORD_HASH"]})
    )
    service = AuthService(
        AuthSettings(
            username="admin",
            password_hash=None,
            session_secret=b"test-secret",
            credential_file=credential_file,
        )
    )

    service.change_password(
        "correct-horse-battery-staple", "a-new-password-123", "test-client"
    )

    assert service.verify_login("admin", "a-new-password-123", "test-client")
    assert not service.verify_login(
        "admin", "correct-horse-battery-staple", "test-client"
    )
    assert credential_file.stat().st_mode & 0o777 == 0o600


def test_password_change_rejects_short_password(tmp_path) -> None:
    service = AuthService(
        AuthSettings(
            username="admin",
            password_hash=__import__("os").environ["SIM_ADMIN_PASSWORD_HASH"],
            session_secret=b"test-secret",
            credential_file=tmp_path / "auth.json",
        )
    )

    try:
        service.change_password("correct-horse-battery-staple", "too-short", "client")
    except PasswordChangeError as exc:
        assert exc.code == "weak_password"
    else:
        raise AssertionError("weak password was accepted")
