"""Pure helpers for the supported SJA5 SUCI-by-ME configuration."""

import base64
import hashlib


def build_suci_calc_info(scheme: int, key_id: int | None, key_hex: str | None) -> dict:
    """Build one protection-scheme entry and its optional HN public key."""
    if scheme == 0:
        return {
            "prot_scheme_id_list": [{"priority": 0, "identifier": 0, "key_index": 0}],
            "hnet_pubkey_list": [],
        }
    if key_id is None or not key_hex:
        raise ValueError("protected SUCI requires a home-network public key")
    return {
        "prot_scheme_id_list": [{"priority": 0, "identifier": scheme, "key_index": 1}],
        "hnet_pubkey_list": [{
            "hnet_pubkey_identifier": key_id,
            "hnet_pubkey": bytes.fromhex(key_hex),
        }],
    }


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

    def active(number: int) -> bool:
        if isinstance(services, dict):
            entry = services.get(number, services.get(str(number), {}))
            return bool(entry.get("activated", False))
        return number in {int(service) for service in services}

    return {
        "routing_indicator": str(routing.get("routing_indicator", "")),
        "protection_scheme": scheme,
        "hn_public_key_id": int(selected_key["hnet_pubkey_identifier"]) if selected_key else None,
        "hn_public_key": key_value,
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
