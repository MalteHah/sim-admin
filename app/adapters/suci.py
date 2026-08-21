"""Pure helpers for the supported SJA5 SUCI-by-ME configuration."""


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
