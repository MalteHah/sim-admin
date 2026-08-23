"""Pure helpers for SJA5/S17 SUCI configuration."""

import base64
import hashlib


def build_suci_calc_info_list(configurations: list[dict]) -> dict:
    """Build ordered protection-scheme and HN-key lists for EF.SUCI_Calc_Info."""
    if not configurations:
        raise ValueError("at least one SUCI configuration is required")
    priorities = [int(item["priority"]) for item in configurations]
    if len(set(priorities)) != len(priorities) or any(value < 0 or value > 255 for value in priorities):
        raise ValueError("SUCI priorities must be unique bytes")
    schemes = []
    keys = []
    key_indexes: dict[tuple[int, str], int] = {}
    for item in sorted(configurations, key=lambda value: int(value["priority"])):
        scheme = int(item["protection_scheme"])
        if scheme not in {0, 1, 2}:
            raise ValueError("unsupported SUCI protection scheme")
        if scheme == 0:
            if item.get("hn_public_key_id") is not None or item.get("hn_public_key"):
                raise ValueError("null scheme cannot use a home-network public key")
            key_index = 0
        else:
            key_id = item.get("hn_public_key_id")
            key_hex = (item.get("hn_public_key") or "").replace(" ", "").upper()
            if key_id is None or not key_hex:
                raise ValueError("protected SUCI requires a home-network public key")
            raw = bytes.fromhex(key_hex)
            if scheme == 1 and len(raw) != 32:
                raise ValueError("protection scheme A requires a 32-byte key")
            if scheme == 2 and len(raw) not in {33, 65}:
                raise ValueError("protection scheme B requires a 33- or 65-byte key")
            key = (int(key_id), key_hex)
            if key not in key_indexes:
                keys.append({"hnet_pubkey_identifier": int(key_id), "hnet_pubkey": raw})
                key_indexes[key] = len(keys)
            key_index = key_indexes[key]
        schemes.append({"priority": int(item["priority"]), "identifier": scheme, "key_index": key_index})
    return {"prot_scheme_id_list": schemes, "hnet_pubkey_list": keys}


def build_suci_calc_info(scheme: int, key_id: int | None, key_hex: str | None) -> dict:
    """Backward-compatible builder for one priority-zero configuration."""
    return build_suci_calc_info_list([{"priority": 0, "protection_scheme": scheme,
        "hn_public_key_id": key_id, "hn_public_key": key_hex}])


def enable_suci_by_me(services: list[int] | dict) -> list[int] | dict:
    """Enable privacy support (124) and disable on-USIM calculation (125)."""
    if isinstance(services, dict):
        result = {key: dict(value) for key, value in services.items()}
        for number, active in ((124, True), (125, False)):
            key = number if number in result else str(number)
            if key not in result:
                raise ValueError(f"UST service {number} is unavailable")
            result[key]["activated"] = active
        return result
    return sorted(({int(service) for service in services} | {124}) - {125})


def enable_suci_by_usim(services: list[int] | dict) -> list[int] | dict:
    """Enable on-USIM SUCI calculation (125) and disable ME calculation (124)."""
    if isinstance(services, dict):
        result = {key: dict(value) for key, value in services.items()}
        for number, active in ((124, False), (125, True)):
            key = number if number in result else str(number)
            if key not in result:
                raise ValueError(f"UST service {number} is unavailable")
            result[key]["activated"] = active
        return result
    return sorted(({int(service) for service in services} | {125}) - {124})


def build_s17_usim_suci_calc_info(scheme: int, key_id: int | None, key_hex: str | None) -> dict:
    """Build the S17 on-USIM configuration; this card mode supports Profile B only."""
    key = (key_hex or "").replace(" ", "").upper()
    if scheme != 2:
        raise ValueError("S17 SUCI calculation on the USIM requires Profile B")
    if key_id is None:
        raise ValueError("S17 SUCI calculation on the USIM requires a key identifier")
    if len(bytes.fromhex(key)) != 65 or not key.startswith("04"):
        raise ValueError("S17 SUCI calculation on the USIM requires an uncompressed 65-byte P-256 key")
    return build_suci_calc_info(2, key_id, key)


def read_suci_card_state(routing: dict, calculation: dict, services: list[int] | dict) -> dict:
    """Normalize decoded pySim 5GS files into JSON-safe comparison values."""
    schemes = calculation.get("prot_scheme_id_list") or []
    selected = min(schemes, key=lambda item: int(item.get("priority", 255))) if schemes else {}
    scheme = int(selected.get("identifier", 0))
    key_index = int(selected.get("key_index", 0))
    keys = calculation.get("hnet_pubkey_list") or []
    selected_key = keys[key_index - 1] if key_index and key_index <= len(keys) else None
    key_value = selected_key.get("hnet_pubkey") if selected_key else None
    if isinstance(key_value, bytes):
        key_value = key_value.hex().upper()
    elif key_value is not None:
        key_value = str(key_value).replace(" ", "").upper()

    configurations = []
    for entry in sorted(schemes, key=lambda item: int(item.get("priority", 255))):
        entry_scheme = int(entry.get("identifier", 0))
        entry_key_index = int(entry.get("key_index", 0))
        entry_key = keys[entry_key_index - 1] if entry_key_index and entry_key_index <= len(keys) else None
        entry_key_value = entry_key.get("hnet_pubkey") if entry_key else None
        if isinstance(entry_key_value, bytes):
            entry_key_value = entry_key_value.hex().upper()
        elif entry_key_value is not None:
            entry_key_value = str(entry_key_value).replace(" ", "").upper()
        configurations.append({
            "priority": int(entry.get("priority", 255)),
            "protection_scheme": entry_scheme,
            "hn_public_key_id": int(entry_key["hnet_pubkey_identifier"]) if entry_key else None,
            "hn_public_key": entry_key_value,
        })

    def active(number: int) -> bool:
        if isinstance(services, dict):
            entry = services.get(number, services.get(str(number), {}))
            return bool(entry.get("activated", False))
        return number in {int(service) for service in services}

    return {
        "routing_indicator": str(routing.get("routing_indicator", "")).zfill(4),
        "protection_scheme": scheme,
        "hn_public_key_id": int(selected_key["hnet_pubkey_identifier"]) if selected_key else None,
        "hn_public_key": key_value,
        "suci_configurations": configurations,
        "suci_service_124_active": active(124),
        "suci_service_125_active": active(125),
    }


def normalize_hnet_public_key(scheme: int, key_data: str) -> tuple[str, str]:
    """Accept public PEM/DER or raw hex and return card bytes plus fingerprint."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec, x25519

    value = key_data.strip()
    if "PRIVATE KEY" in value.upper():
        raise ValueError("Private Schlüssel werden nicht angenommen")
    try:
        if value.startswith("-----BEGIN"):
            public_key = serialization.load_pem_public_key(value.encode())
        elif value.startswith("base64:"):
            public_key = serialization.load_der_public_key(base64.b64decode(value[7:], validate=True))
        else:
            raw = bytes.fromhex("".join(value.split()).replace(":", ""))
            if scheme == 1:
                public_key = x25519.X25519PublicKey.from_public_bytes(raw)
            elif scheme == 2:
                public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)
            else:
                raise ValueError("Nur Profile A und B können Schlüssel verwenden")
    except (TypeError, ValueError, base64.binascii.Error) as exc:
        raise ValueError("Die öffentliche Schlüsseldatei ist ungültig") from exc

    if scheme == 1 and isinstance(public_key, x25519.X25519PublicKey):
        raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    elif scheme == 2 and isinstance(public_key, ec.EllipticCurvePublicKey) and isinstance(public_key.curve, ec.SECP256R1):
        raw = public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    else:
        raise ValueError("Schlüsseltyp und SUCI-Schutzverfahren passen nicht zusammen")
    return raw.hex().upper(), hashlib.sha256(raw).hexdigest().upper()
