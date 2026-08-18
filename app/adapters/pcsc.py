"""PC/SC implementation of smart-card reader discovery."""

from app.adapters.readers import ReaderAdapterError
from app.models import Reader, ReaderStatus


class PcscReaderAdapter:
    """Discover readers through pyscard without reading SIM contents."""

    def list_readers(self) -> list[Reader]:
        try:
            from smartcard.scard import (
                SCARD_E_NO_READERS_AVAILABLE,
                SCARD_SCOPE_USER,
                SCARD_STATE_PRESENT,
                SCARD_STATE_UNAWARE,
                SCARD_S_SUCCESS,
                SCardEstablishContext,
                SCardGetStatusChange,
                SCardListReaders,
                SCardReleaseContext,
            )
        except ImportError as exc:
            raise ReaderAdapterError("PC/SC support is not installed") from exc

        result, context = SCardEstablishContext(SCARD_SCOPE_USER)
        if result != SCARD_S_SUCCESS:
            raise ReaderAdapterError("PC/SC context is unavailable")

        try:
            result, reader_names = SCardListReaders(context, [])
            if result == SCARD_E_NO_READERS_AVAILABLE:
                return []
            if result != SCARD_S_SUCCESS:
                raise ReaderAdapterError("PC/SC reader discovery failed")

            discovered: list[Reader] = []
            for reader_name in reader_names:
                result, states = SCardGetStatusChange(
                    context,
                    0,
                    [(reader_name, SCARD_STATE_UNAWARE)],
                )

                status = ReaderStatus.ERROR
                atr: str | None = None
                if result == SCARD_S_SUCCESS:
                    _, event_state, atr_bytes = states[0]
                    if event_state & SCARD_STATE_PRESENT:
                        status = ReaderStatus.CARD_PRESENT
                        atr = " ".join(f"{byte:02X}" for byte in atr_bytes)
                    else:
                        status = ReaderStatus.READY

                discovered.append(
                    Reader(
                        name=reader_name,
                        reader_type="pcsc",
                        status=status,
                        atr=atr,
                    )
                )

            return discovered
        finally:
            SCardReleaseContext(context)
