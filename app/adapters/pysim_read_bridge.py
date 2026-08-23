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

                acc_readable = False
                acc = None
                try:
                    channel.select("MF/ADF.USIM/EF.ACC")
                    acc_raw, _ = channel.read_binary()
                    acc = acc_raw.upper()
                    acc_readable = True
                except Exception:
                    pass

                msisdn_readable = False
                msisdn = None
                try:
                    channel.select("MF/DF.TELECOM/EF.MSISDN")
                    msisdn_data, _ = channel.read_record_dec(1)
                    msisdn = msisdn_data.get("dialing_nr") or msisdn_data.get("msisdn") or None
                    if msisdn:
                        msisdn = str(msisdn).rstrip("fF")
                    msisdn_readable = True
                except Exception:
                    pass

                suci_supported = False
                suci_readable = False
                suci_state = {}
                ims_supported = False
                ims_readable = False
                ims_state = {}
                try:
                    from pySim.sysmocom_sja2 import SysmocomSJA5
                    suci_supported = transport.get_atr().lower() in SysmocomSJA5._atrs
                    ims_supported = suci_supported
                    if suci_supported:
                        from suci import read_suci_card_state
                        channel.select("MF/ADF.USIM/DF.5GS/EF.Routing_Indicator")
                        routing_data, _ = channel.read_binary_dec()
                        channel.select("MF/ADF.USIM/DF.5GS/EF.SUCI_Calc_Info")
                        calculation_data, _ = channel.read_binary_dec()
                        channel.select("MF/ADF.USIM/EF.UST")
                        service_data, _ = channel.read_binary_dec()
                        suci_state = read_suci_card_state(routing_data, calculation_data, service_data)
                        suci_readable = True
                except Exception:
                    suci_readable = False
                try:
                    if ims_supported:
                        channel.select("MF/ADF.ISIM/EF.IMPI")
                        raw, _ = channel.read_binary()
                        impi = None if set(raw.lower()) <= {"f"} else channel.read_binary_dec()[0].get("nai")
                        channel.select("MF/ADF.ISIM/EF.IMPU")
                        raw, _ = channel.read_record(1)
                        impu = None if set(raw.lower()) <= {"f"} else channel.read_record_dec(1)[0].get("impu")
                        channel.select("MF/ADF.ISIM/EF.DOMAIN")
                        raw, _ = channel.read_binary()
                        domain = None if set(raw.lower()) <= {"f"} else channel.read_binary_dec()[0].get("domain")
                        channel.select("MF/ADF.ISIM/EF.IST")
                        raw, _ = channel.read_binary()
                        ist = None if not raw or set(raw.lower()) <= {"0", "f"} else raw.upper()
                        ims_state = {"impi": impi, "impu": impu, "ims_domain": domain, "ist": ist}
                        ims_readable = True
                except Exception:
                    ims_readable = False

        print(
            json.dumps(
                {
                    "reader_index": args.reader,
                    "card_type": str(runtime.profile),
                    "atr": transport.get_atr().upper(),
                    "iccid": iccid_data["iccid"],
                    "imsi": imsi_data["imsi"],
                    "acc_readable": acc_readable,
                    "acc": acc,
                    "msisdn_readable": msisdn_readable,
                    "msisdn": msisdn,
                    "ims_supported": ims_supported,
                    "ims_readable": ims_readable,
                    **ims_state,
                    "suci_supported": suci_supported,
                    "suci_readable": suci_readable,
                    **suci_state,
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
