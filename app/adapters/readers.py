"""Contracts and errors for smart-card reader adapters."""

from typing import Protocol

from app.models import Reader


class ReaderAdapterError(RuntimeError):
    """Raised when the reader subsystem cannot be queried."""


class ReaderAdapter(Protocol):
    """Technology-independent reader discovery contract."""

    def list_readers(self) -> list[Reader]:
        """Return all currently available smart-card readers."""
