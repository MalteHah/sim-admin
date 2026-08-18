"""Reader-related application services."""

from app.adapters.readers import ReaderAdapter
from app.models import Reader


class ReaderService:
    """Expose reader use cases without leaking adapter details."""

    def __init__(self, adapter: ReaderAdapter) -> None:
        self._adapter = adapter

    def list_readers(self) -> list[Reader]:
        return self._adapter.list_readers()
