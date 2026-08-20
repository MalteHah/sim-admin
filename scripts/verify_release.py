#!/usr/bin/env python3
"""Verify a SIM-Admin release checksum and Ed25519 signature."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()

    archive = args.archive.resolve()
    checksum_file = archive.with_suffix(archive.suffix + ".sha256")
    signature = archive.with_suffix(archive.suffix + ".sig")
    for path in (archive, checksum_file, signature, args.public_key):
        if not path.is_file():
            raise SystemExit(f"Erforderliche Datei fehlt: {path}")

    parts = checksum_file.read_text(encoding="ascii").strip().split()
    if len(parts) != 2 or parts[1] != archive.name:
        raise SystemExit("Ungültiges Prüfsummenformat oder falscher Dateiname")
    if parts[0].lower() != sha256(archive):
        raise SystemExit("SHA-256-Prüfung fehlgeschlagen")

    verification = subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-rawin", "-pubin",
         "-inkey", str(args.public_key), "-sigfile", str(signature),
         "-in", str(archive)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if verification.returncode != 0:
        raise SystemExit("Signaturprüfung fehlgeschlagen")
    print(f"Release geprüft: {archive.name}")


if __name__ == "__main__":
    main()
