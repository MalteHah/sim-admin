"""Subprocess boundary to the separately installed pySim environment."""

import json
import os
from pathlib import Path
import subprocess
from threading import Lock

from pydantic import ValidationError

from app.adapters.sim_cards import SIMReadError, SIMWriteError
from app.models import SIMReadResult

DEFAULT_PYSIM_PYTHON = "/opt/sim-admin/venv/bin/python"
DEFAULT_PYSIM_SOURCE = "/opt/sim-admin/pysim"
BRIDGE_SCRIPT = Path(__file__).with_name("pysim_read_bridge.py")
WRITE_BRIDGE_SCRIPT = Path(__file__).with_name("pysim_write_bridge.py")


class PySimCardAdapter:
    """Run read-only pySim operations outside the web-server process."""

    def __init__(
        self,
        python_executable: str | None = None,
        pysim_source: str | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self._python = python_executable or os.getenv(
            "SIM_ADMIN_PYSIM_PYTHON", DEFAULT_PYSIM_PYTHON
        )
        self._pysim_source = pysim_source or os.getenv(
            "SIM_ADMIN_PYSIM_SOURCE", DEFAULT_PYSIM_SOURCE
        )
        self._timeout_seconds = timeout_seconds
        self._lock = Lock()

    def read_identity(self, reader_index: int = 0) -> SIMReadResult:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = self._pysim_source
        try:
            with self._lock:
                result = subprocess.run(
                    [
                        self._python,
                        str(BRIDGE_SCRIPT),
                        "--reader",
                        str(reader_index),
                    ],
                    capture_output=True,
                    check=False,
                    env=environment,
                    text=True,
                    timeout=self._timeout_seconds,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SIMReadError("pysim_unavailable", "pySim ist nicht erreichbar") from exc

        try:
            json_line = next(
                line for line in reversed(result.stdout.splitlines()) if line.strip()
            )
            payload = json.loads(json_line)
        except (json.JSONDecodeError, StopIteration) as exc:
            raise SIMReadError(
                "invalid_response", "pySim lieferte keine gültige Antwort"
            ) from exc

        if result.returncode != 0:
            raise SIMReadError(
                str(payload.get("error", "read_failed")),
                str(payload.get("message", "SIM konnte nicht gelesen werden")),
            )

        try:
            return SIMReadResult.model_validate(payload)
        except ValidationError as exc:
            raise SIMReadError(
                "invalid_response", "pySim lieferte unvollständige Kartendaten"
            ) from exc

    def write_standard_fields(self, reader_index: int, expected_iccid: str, imsi: str, acc: str, msisdn: str | None, adm: str, fields: list[str], ki: str | None = None, opc: str | None = None) -> list[str]:
        environment = os.environ.copy(); environment["PYTHONPATH"] = self._pysim_source
        payload = json.dumps({"expected_iccid": expected_iccid, "imsi": imsi, "acc": acc, "msisdn": msisdn, "adm": adm, "fields": fields, "ki": ki, "opc": opc})
        try:
            with self._lock:
                result = subprocess.run([self._python, str(WRITE_BRIDGE_SCRIPT), "--reader", str(reader_index)], input=payload, capture_output=True, check=False, env=environment, text=True, timeout=self._timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SIMWriteError("pysim_unavailable", "pySim ist nicht erreichbar") from exc
        try:
            response = json.loads(next(line for line in reversed(result.stdout.splitlines()) if line.strip()))
        except (json.JSONDecodeError, StopIteration) as exc:
            raise SIMWriteError("invalid_response", "pySim lieferte keine gültige Antwort") from exc
        if result.returncode != 0:
            raise SIMWriteError(str(response.get("error", "write_failed")), str(response.get("message", "SIM konnte nicht geschrieben werden")))
        return [str(field) for field in response.get("verified_fields", [])]
