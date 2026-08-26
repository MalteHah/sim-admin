from pathlib import Path
import subprocess

from scripts.build_release import external_files


def test_external_pysim_files_exclude_repository_metadata(tmp_path: Path) -> None:
    source = tmp_path / "pysim"
    (source / "pySim").mkdir(parents=True)
    (source / ".git").mkdir()
    (source / "pySim" / "__pycache__").mkdir()
    (source / "pySim-shell.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (source / "pySim" / "app.py").write_text("", encoding="utf-8")
    (source / ".git" / "config").write_text("secret", encoding="utf-8")
    (source / "pySim" / "__pycache__" / "app.pyc").write_bytes(b"cache")

    bundled = external_files(source, Path("pysim"))

    assert [relative.as_posix() for relative, _ in bundled] == [
        "pysim/pySim/app.py",
        "pysim/pySim-shell.py",
    ]


def test_install_script_has_valid_posix_shell_syntax() -> None:
    install_script = Path(__file__).resolve().parents[1] / "scripts" / "install.sh"
    result = subprocess.run(
        ["sh", "-n", str(install_script)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
