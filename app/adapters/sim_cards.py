"""Contracts and errors for read-only SIM access."""

from typing import Protocol

from app.models import SIMReadResult


class SIMReadError(RuntimeError):
    """A safe, classified error returned by a SIM adapter."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SIMWriteError(RuntimeError):
    """A classified write error which never contains secret values."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SIMCardAdapter(Protocol):
    """Technology-independent contract for read-only SIM inspection."""

    def read_identity(self, reader_index: int = 0) -> SIMReadResult:
        """Read non-secret card identifiers without changing the card."""

    def write_standard_fields(self, reader_index: int, expected_iccid: str, imsi: str, acc: str, msisdn: str | None, adm: str, fields: list[str], ki: str | None = None, opc: str | None = None,
        impi: str | None = None, impu: str | None = None, ims_domain: str | None = None, ist: str | None = None,
        routing_indicator: str | None = None, protection_scheme: int | None = None,
        hn_public_key_id: int | None = None, hn_public_key: str | None = None,
        spn: str | None = None) -> list[str]:
        """Write and verify supported fields after an ICCID and card-model check."""
