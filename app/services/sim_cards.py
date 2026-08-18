"""Read-only SIM application services."""

from app.adapters.sim_cards import SIMCardAdapter
from app.models import SIMReadResult


class SIMCardService:
    """Coordinate safe, read-only card inspection."""

    def __init__(self, adapter: SIMCardAdapter) -> None:
        self._adapter = adapter

    def read_identity(self, reader_index: int = 0) -> SIMReadResult:
        return self._adapter.read_identity(reader_index)
