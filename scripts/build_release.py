#!/usr/bin/env python3
"""Build a deterministic SIM-Admin release archive and checksum."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parent.parent


def git_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8")
    return sorted(Path(item) for item in output.split("\0") if item)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--signing-key", type=Path)
    parser.add_argument("--signing-key-password-file", type=Path)
    args = parser.parse_args()

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not version or any(character not in "0123456789." for character in version):
        raise SystemExit("VERSION muss eine numerische Punktnotation enthalten")
    if not args.allow_dirty:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        )
        if status:
            raise SystemExit("Release-Bau abgebrochen: Arbeitsverzeichnis ist nicht sauber")

    files = git_files()
    manifest = {
        "application": "sim-admin",
        "format": 1,
        "version": version,
        "files": [
            {"path": str(path), "sha256": sha256(ROOT / path)} for path in files
        ],
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    prefix = f"sim-admin-{version}"
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f"{prefix}.tar.gz"

    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for relative in files:
                    source = ROOT / relative
                    info = tar.gettarinfo(str(source), arcname=f"{prefix}/{relative}")
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    info.mtime = 0
                    with source.open("rb") as handle:
                        tar.addfile(info, handle)
                info = tarfile.TarInfo(f"{prefix}/release-manifest.json")
                info.size = len(manifest_bytes)
                info.mode = 0o644
                info.mtime = info.uid = info.gid = 0
                info.uname = info.gname = "root"
                tar.addfile(info, io.BytesIO(manifest_bytes))

    checksum = sha256(archive)
    checksum_file = archive.with_suffix(archive.suffix + ".sha256")
    checksum_file.write_text(f"{checksum}  {archive.name}\n", encoding="ascii")
    print(archive)
    print(checksum_file)
    if args.signing_key:
        signing_key = args.signing_key.expanduser().resolve()
        if not signing_key.is_file():
            raise SystemExit("Privater Signierschlüssel wurde nicht gefunden")
        signature = archive.with_suffix(archive.suffix + ".sig")
        public_key = archive.with_suffix(archive.suffix + ".pub.pem")
        password_arguments: list[str] = []
        if args.signing_key_password_file:
            password_file = args.signing_key_password_file.expanduser().resolve()
            if not password_file.is_file():
                raise SystemExit("Passwortdatei für den Signierschlüssel wurde nicht gefunden")
            password_arguments = ["-passin", f"file:{password_file}"]
        subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", *password_arguments, "-inkey", str(signing_key),
             "-in", str(archive), "-out", str(signature)],
            check=True,
        )
        with public_key.open("wb") as handle:
            subprocess.run(
                ["openssl", "pkey", "-in", str(signing_key), *password_arguments, "-pubout"],
                stdout=handle,
                check=True,
            )
        print(signature)
        print(public_key)


if __name__ == "__main__":
    main()
