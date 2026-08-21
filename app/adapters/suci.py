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


def enable_suci_by_me(services: list[int]) -> list[int]:
    """Enable privacy support (124) and disable on-USIM calculation (125)."""
    return sorted(({int(service) for service in services} | {124}) - {125})


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
