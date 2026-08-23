"""Single-purpose pySim bridge for guarded standard-field updates."""

import argparse
import json
import sys

from pysim_read_bridge import card_is_present, emit_error
from suci import build_s17_usim_suci_calc_info, build_suci_calc_info, enable_suci_by_me, enable_suci_by_usim


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--reader", type=int, default=0); args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        from pySim.app import init_card
        from pySim.exceptions import NoCardError, ProtocolError, ReaderError
        from pySim.transport.pcsc import PcscSimLink
        from pySim.utils import h2b, sanitize_pin_adm
    except (ImportError, json.JSONDecodeError):
        emit_error("invalid_request", "Schreibauftrag oder pySim ist nicht verfügbar", 3)

    fields = set(payload.get("fields", []))
    fivegs_fields = {"routing_indicator", "suci_calculation_mode", "protection_scheme", "hn_public_key_id", "hn_public_key"}
    if not fields or not fields <= {"imsi", "msisdn", "acc", "ki", "opc", "impi", "impu", "ims_domain", "ist"} | fivegs_fields:
        emit_error("unsupported_fields", "Der Entwurf enthält noch nicht unterstützte Schreibfelder", 4)
    transport = None
    stage = "initialization"
    try:
        if not card_is_present(args.reader): emit_error("no_card", "Keine SIM-Karte eingelegt", 2)
        options = argparse.Namespace(pcsc_dev=args.reader, pcsc_regex=None, pcsc_shared=True)
        transport = PcscSimLink(options); runtime, card = init_card(transport)
        if runtime is None: emit_error("unsupported_card", "Kartentyp wird nicht unterstützt", 4)
        channel = runtime.lchan[0]
        channel.select("MF/EF.ICCID"); current_iccid, _ = channel.read_binary_dec()
        if current_iccid["iccid"] != payload["expected_iccid"]:
            emit_error("iccid_mismatch", "Die eingelegte Karte gehört nicht zum ausgewählten Profil", 5)
        stage = "adm_verification"
        pin_adm = sanitize_pin_adm(payload["adm"])
        try:
            _response, sw = channel.scc.verify_chv(card._adm_chv_num, h2b(pin_adm))
        except Exception:
            emit_error("adm_verification_failed", "ADM1 wurde von der Karte abgelehnt", 6)
        if sw != "9000": emit_error("adm_verification_failed", "ADM1 wurde von der Karte abgelehnt", 6)
        if fields & ({"ki", "opc", "impi", "impu", "ims_domain", "ist"} | fivegs_fields):
            from pySim.sysmocom_sja2 import SysmocomSJA5
            if transport.get_atr().lower() not in SysmocomSJA5._atrs:
                code = "unsupported_card_for_ims" if fields & ({"impi", "impu", "ims_domain", "ist"} | fivegs_fields) else "unsupported_card_for_auth_keys"
                emit_error(code, "Diese Felder werden nur für erkannte SysmocomSJA5-Karten unterstützt", 11)

        # Resolve and read every affected 5GS file before the first mutation.
        # This prevents a missing or inaccessible file from causing a partial write.
        current_routing = None
        if "routing_indicator" in fields:
            stage = "routing_indicator_preflight"
            channel.select("MF/ADF.USIM/DF.5GS/EF.Routing_Indicator")
            current_routing, _ = channel.read_binary_dec()
        suci_fields = {"suci_calculation_mode", "protection_scheme", "hn_public_key_id", "hn_public_key"}
        current_ust = None
        target_suci = None
        if fields & suci_fields:
            stage = "suci_preflight"
            suci_mode = payload.get("suci_calculation_mode", "me")
            target_suci = (build_s17_usim_suci_calc_info if suci_mode == "usim" else build_suci_calc_info)(
                payload.get("protection_scheme"), payload.get("hn_public_key_id"), payload.get("hn_public_key"))
            target_suci_path = "MF/ADF.USIM/DF.SAIP/EF.SUCI_Calc_Info" if suci_mode == "usim" else "MF/ADF.USIM/DF.5GS/EF.SUCI_Calc_Info"
            try:
                channel.select(target_suci_path)
            except Exception:
                if suci_mode == "usim":
                    emit_error("suci_usim_unsupported", "SUCI-Berechnung auf der USIM wird von dieser Karte nicht unterstützt", 14)
                raise
            channel.read_binary_dec()
            channel.select("MF/ADF.USIM/EF.UST")
            current_ust, _ = channel.read_binary_dec()

        verified = []
        if "imsi" in fields:
            stage = "imsi"
            channel.select("MF/ADF.USIM/EF.IMSI"); channel.update_binary_dec({"imsi": payload["imsi"]})
            value, _ = channel.read_binary_dec()
            if value.get("imsi") != payload["imsi"]: emit_error("verification_failed", "IMSI konnte nicht bestätigt werden", 7)
            verified.append("imsi")
        if "acc" in fields:
            stage = "acc"
            channel.select("MF/ADF.USIM/EF.ACC"); channel.update_binary(payload["acc"].lower())
            raw, _ = channel.read_binary()
            if raw.lower() != payload["acc"].lower(): emit_error("verification_failed", "ACC konnte nicht bestätigt werden", 7)
            verified.append("acc")
        if "msisdn" in fields:
            stage = "msisdn"
            number = (payload.get("msisdn") or "").lstrip("+")
            channel.select("MF/DF.TELECOM/EF.MSISDN"); channel.update_record_dec(1, {"msisdn": number})
            value, _ = channel.read_record_dec(1)
            if value.get("dialing_nr", "").rstrip("f") != number: emit_error("verification_failed", "MSISDN konnte nicht bestätigt werden", 7)
            verified.append("msisdn")
        if fields & {"ki", "opc"}:
            stage = "authentication_keys"
            key = h2b(payload["ki"]); opc = h2b(payload["opc"])
            auth_3g = {"cfg": {"only_4bytes_res_in_3g": False, "sres_deriv_func_in_2g": 1, "use_opc_instead_of_op": True, "algorithm": "milenage"}, "key": key, "op_opc": opc}
            auth_2g = {"cfg": {"only_4bytes_res_in_3g": False, "sres_deriv_func_in_2g": 1, "use_opc_instead_of_op": True, "algorithm": "milenage"}, "key": key, "op_opc": opc}
            for path, value_to_write in (("MF/ADF.USIM/EF.USIM_AUTH_KEY", auth_3g), ("MF/ADF.USIM/EF.USIM_AUTH_KEY_2G", auth_2g)):
                channel.select(path); channel.update_binary_dec(value_to_write); value, _ = channel.read_binary_dec()
                if value.get("key") != key or value.get("op_opc") != opc or not value.get("cfg", {}).get("use_opc_instead_of_op"):
                    emit_error("verification_failed", "Authentisierungsparameter konnten nicht bestätigt werden", 7)
            if "ki" in fields: verified.append("ki")
            if "opc" in fields: verified.append("opc")
        if fields & {"impi", "impu", "ims_domain", "ist"}:
            stage = "ims"
            if "impi" in fields:
                channel.select("MF/ADF.ISIM/EF.IMPI")
                if payload["impi"] is None:
                    current, _ = channel.read_binary(); target = "ff" * (len(current) // 2)
                    channel.update_binary(target); value, _ = channel.read_binary()
                    if value.lower() != target: emit_error("verification_failed", "Löschen der IMPI konnte nicht bestätigt werden", 7)
                else:
                    channel.update_binary_dec({"nai": payload["impi"]}); value, _ = channel.read_binary_dec()
                    if value.get("nai") != payload["impi"]: emit_error("verification_failed", "IMPI konnte nicht bestätigt werden", 7)
                verified.append("impi")
            if "ims_domain" in fields:
                channel.select("MF/ADF.ISIM/EF.DOMAIN")
                if payload["ims_domain"] is None:
                    current, _ = channel.read_binary(); target = "ff" * (len(current) // 2)
                    channel.update_binary(target); value, _ = channel.read_binary()
                    if value.lower() != target: emit_error("verification_failed", "Löschen der IMS-Domain konnte nicht bestätigt werden", 7)
                else:
                    channel.update_binary_dec({"domain": payload["ims_domain"]}); value, _ = channel.read_binary_dec()
                    if value.get("domain") != payload["ims_domain"]: emit_error("verification_failed", "IMS-Domain konnte nicht bestätigt werden", 7)
                verified.append("ims_domain")
            if "impu" in fields:
                channel.select("MF/ADF.ISIM/EF.IMPU")
                if payload["impu"] is None:
                    current, _ = channel.read_record(1); target = "ff" * (len(current) // 2)
                    channel.update_record(1, target); value, _ = channel.read_record(1)
                    if value.lower() != target: emit_error("verification_failed", "Löschen der IMPU konnte nicht bestätigt werden", 7)
                else:
                    channel.update_record_dec(1, {"impu": payload["impu"]}); value, _ = channel.read_record_dec(1)
                    if value.get("impu") != payload["impu"]: emit_error("verification_failed", "IMPU konnte nicht bestätigt werden", 7)
                verified.append("impu")
            if "ist" in fields:
                channel.select("MF/ADF.ISIM/EF.IST"); current, _ = channel.read_binary()
                target = payload["ist"].lower() if payload["ist"] is not None else "00" * (len(current) // 2)
                if len(target) != len(current): emit_error("invalid_ist_length", "IST muss exakt der Dateigröße der Karte entsprechen", 13)
                channel.update_binary(target); value, _ = channel.read_binary()
                if value.lower() != target: emit_error("verification_failed", "IST konnte nicht bestätigt werden", 7)
                verified.append("ist")
        if "routing_indicator" in fields:
            stage = "routing_indicator"
            channel.select("MF/ADF.USIM/DF.5GS/EF.Routing_Indicator")
            target = {"routing_indicator": payload["routing_indicator"], "rfu": current_routing.get("rfu", b"\xff\xff")}
            channel.update_binary_dec(target); value, _ = channel.read_binary_dec()
            if value.get("routing_indicator") != payload["routing_indicator"]:
                emit_error("verification_failed", "Routing Indicator konnte nicht bestätigt werden", 7)
            verified.append("routing_indicator")
        if fields & suci_fields:
            stage = "suci_calc_info"
            target = target_suci
            channel.select(target_suci_path)
            channel.update_binary_dec(target); value, _ = channel.read_binary_dec()
            if value != target: emit_error("verification_failed", "SUCI-Konfiguration konnte nicht bestätigt werden", 7)
            stage = "ust_services"
            channel.select("MF/ADF.USIM/EF.UST")
            target_ust = enable_suci_by_usim(current_ust) if suci_mode == "usim" else enable_suci_by_me(current_ust)
            channel.update_binary_dec(target_ust); value, _ = channel.read_binary_dec()
            if value != target_ust: emit_error("verification_failed", "SUCI-Dienste 124/125 konnten nicht bestätigt werden", 7)
            for field in sorted(fields & suci_fields): verified.append(field)
        print(json.dumps({"verified_fields": verified}))
    except NoCardError: emit_error("no_card", "Keine SIM-Karte eingelegt", 2)
    except ReaderError: emit_error("reader_error", "Kartenleser ist nicht verfügbar", 8)
    except ProtocolError: emit_error("protocol_error", "SIM-Karte antwortet nicht", 9)
    except Exception: emit_error(f"write_failed_{stage}", f"SIM-Schreibvorgang ist in der Stufe {stage} fehlgeschlagen", 10)
    finally:
        if transport is not None:
            try: transport.disconnect()
            except Exception: pass


if __name__ == "__main__": main()
