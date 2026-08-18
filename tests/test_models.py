"""Tests for the initial domain model and its safety properties."""

import pytest
from pydantic import ValidationError

from app.models import (
    FiveGSProfile,
    HomeNetworkPublicKey,
    IMSProfile,
    Reader,
    ReaderStatus,
    SIMProfile,
)


def test_reader_defaults_to_disconnected() -> None:
    reader = Reader(name="Identiv uTrust", atr="3B 00")

    assert reader.status is ReaderStatus.DISCONNECTED


def test_sim_profile_accepts_valid_identifiers() -> None:
    profile = SIMProfile(
        iccid="8949012345678901234",
        imsi="001010123456789",
        msisdn="+491701234567",
        ki="00112233445566778899AABBCCDDEEFF",
    )

    assert profile.imsi == "001010123456789"


def test_sim_secrets_are_redacted_in_model_representation() -> None:
    profile = SIMProfile(
        iccid="8949012345678901234",
        imsi="001010123456789",
        ki="00112233445566778899AABBCCDDEEFF",
    )

    assert "00112233445566778899AABBCCDDEEFF" not in repr(profile)


def test_invalid_imsi_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SIMProfile(iccid="8949012345678901234", imsi="not-an-imsi")


def test_ims_profile() -> None:
    profile = IMSProfile(
        impi="001010123456789@ims.mnc001.mcc001.3gppnetwork.org",
        impu="sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org",
        domain="ims.mnc001.mcc001.3gppnetwork.org",
        ist="01FF",
    )

    assert profile.ist == "01FF"


def test_five_gs_profile_with_public_key() -> None:
    profile = FiveGSProfile(
        routing_indicator="0001",
        protection_scheme=1,
        public_keys=[HomeNetworkPublicKey(identifier=1, value="AABBCCDD")],
    )

    assert profile.public_keys[0].identifier == 1
