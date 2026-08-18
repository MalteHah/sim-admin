"""JSON-only bridge executed inside the dedicated pySim environment."""

import argparse
from contextlib import redirect_stdout
import json
import os


def emit_error(code: str, message: str, exit_code: int) -> None:
    print(json.dumps({"error": code, "message": message}))
    raise SystemExit(exit_code)


def card_is_present(reader_index: int) -> bool:
    """Check presence without opening or selecting anything on the card."""
    from smartcard.scard import (
        SCARD_SCOPE_USER,
        SCARD_STATE_PRESENT,
        SCARD_STATE_UNAWARE,
        SCARD_S_SUCCESS,
        SCardEstablishContext,
        SCardGetStatusChange,
        SCardListReaders,
        SCardReleaseContext,
    )

    result, context = SCardEstablishContext(SCARD_SCOPE_USER)
    if result != SCARD_S_SUCCESS:
        return False
    try:
        result, readers = SCardListReaders(context, [])
        if result != SCARD_S_SUCCESS or reader_index >= len(readers):
            return False
        result, states = SCardGetStatusChange(
            context,
            0,
            [(readers[reader_index], SCARD_STATE_UNAWARE)],
        )
        return result == SCARD_S_SUCCESS and bool(states[0][1] & SCARD_STATE_PRESENT)
    finally:
        SCardReleaseContext(context)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reader", type=int, default=0)
    args = parser.parse_args()

    try:
        from pySim.app import init_card
        from pySim.exceptions import NoCardError, ProtocolError, ReaderError
        from pySim.transport.pcsc import PcscSimLink
    except ImportError:
        emit_error("pysim_unavailable", "pySim ist nicht installiert", 3)

    options = argparse.Namespace(
        pcsc_dev=args.reader,
        pcsc_regex=None,
        pcsc_shared=True,
    )
    transport = None

    try:
        if not card_is_present(args.reader):
            emit_error("no_card", "Keine SIM-Karte eingelegt", 2)
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            with redirect_stdout(devnull):
                transport = PcscSimLink(options)
                runtime, _card = init_card(transport)
                if runtime is None:
                    emit_error("unsupported_card", "Kartentyp wird nicht unterstützt", 4)

                channel = runtime.lchan[0]
                channel.select("MF/EF.ICCID")
                iccid_data, _ = channel.read_binary_dec()

                try:
                    channel.select("MF/ADF.USIM/EF.IMSI")
                except Exception:
                    channel.select("MF/DF.GSM/EF.IMSI")
                imsi_data, _ = channel.read_binary_dec()

        print(
            json.dumps(
                {
                    "reader_index": args.reader,
                    "card_type": str(runtime.profile),
                    "atr": transport.get_atr().upper(),
                    "iccid": iccid_data["iccid"],
                    "imsi": imsi_data["imsi"],
                }
            )
        )
    except NoCardError:
        emit_error("no_card", "Keine SIM-Karte eingelegt", 2)
    except ReaderError:
        emit_error("reader_error", "Kartenleser ist nicht verfügbar", 5)
    except ProtocolError:
        emit_error("protocol_error", "SIM-Karte antwortet nicht", 6)
    except (KeyError, ValueError):
        emit_error("invalid_card_data", "Kartendaten konnten nicht dekodiert werden", 7)
    except Exception:
        emit_error("read_failed", "SIM-Karte konnte nicht gelesen werden", 8)
    finally:
        if transport is not None:
            try:
                transport.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    main()
