#!/usr/bin/env python3
"""Inspect a signed SIM-Admin offline update without changing the system."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_APPLICATION = Path("/opt/sim-admin/application")
DEFAULT_PUBLIC_KEY = Path("/etc/sim-admin/release-signing-key.pub.pem")


def digest(handle) -> str:
    result = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        result.update(chunk)
    return result.hexdigest()


def version_tuple(value: str) -> tuple[int, ...]:
    try:
        parts = tuple(int(item) for item in value.split("."))
    except ValueError as exc:
        raise ValueError(f"Ungültige Version: {value}") from exc
    if not parts or any(item < 0 for item in parts):
        raise ValueError(f"Ungültige Version: {value}")
    return parts


def inspect_archive(archive: Path) -> tuple[str, int]:
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if not members:
            raise ValueError("Release-Archiv ist leer")
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Release-Archiv enthält einen unsicheren Pfad")
            if not member.isfile():
                raise ValueError("Release-Archiv enthält einen unzulässigen Dateityp")
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        if len(roots) != 1:
            raise ValueError("Release-Archiv besitzt kein eindeutiges Wurzelverzeichnis")
        root = next(iter(roots))
        manifest_name = f"{root}/release-manifest.json"
        try:
            manifest_member = bundle.getmember(manifest_name)
        except KeyError as exc:
            raise ValueError("Release-Manifest fehlt") from exc
        manifest_handle = bundle.extractfile(manifest_member)
        if manifest_handle is None:
            raise ValueError("Release-Manifest kann nicht gelesen werden")
        manifest = json.load(manifest_handle)
        if manifest.get("application") != "sim-admin" or manifest.get("format") != 1:
            raise ValueError("Release-Manifest ist nicht kompatibel")
        version = str(manifest.get("version", ""))
        version_tuple(version)
        expected = {str(item["path"]): str(item["sha256"]).lower() for item in manifest.get("files", [])}
        actual_names = {member.name.removeprefix(f"{root}/") for member in members if member.name != manifest_name}
        if set(expected) != actual_names:
            raise ValueError("Dateiliste und Release-Manifest stimmen nicht überein")
        for relative, checksum in expected.items():
            member = bundle.getmember(f"{root}/{relative}")
            handle = bundle.extractfile(member)
            if handle is None or digest(handle) != checksum:
                raise ValueError("Eine Datei im Release-Archiv ist beschädigt")
        return version, len(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--application", type=Path, default=DEFAULT_APPLICATION)
    parser.add_argument("--public-key", type=Path, default=DEFAULT_PUBLIC_KEY)
    args = parser.parse_args()

    archive = args.archive.resolve()
    verification = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "verify_release.py"), str(archive),
         "--public-key", str(args.public_key)],
    )
    if verification.returncode != 0:
        raise SystemExit("Offline-Update abgewiesen: Signaturprüfung fehlgeschlagen")
    try:
        release_version, file_count = inspect_archive(archive)
        installed_version = (args.application / "VERSION").read_text(encoding="utf-8").strip()
        installed = version_tuple(installed_version)
        release = version_tuple(release_version)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, tarfile.TarError) as exc:
        raise SystemExit(f"Offline-Update abgewiesen: {exc}") from exc

    free = shutil.disk_usage(args.application).free
    required = archive.stat().st_size * 3
    if free < required:
        raise SystemExit("Offline-Update abgewiesen: Nicht genügend freier Speicher")

    if release < installed:
        state = "älter als die installierte Version – Downgrade gesperrt"
    elif release == installed:
        state = "bereits installiert"
    else:
        state = "als Update geeignet"
    print(f"Installierte Version: {installed_version}")
    print(f"Geprüfte Release-Version: {release_version}")
    print(f"Geprüfte Dateien: {file_count}")
    print(f"Status: {state}")
    print("Es wurden keine Änderungen vorgenommen.")


if __name__ == "__main__":
    main()
