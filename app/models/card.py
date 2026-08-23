"""Read-only card identification models."""

from pydantic import Field

from app.models.common import DomainModel


class SuciConfiguration(DomainModel):
    """One ordered protection-scheme entry read from EF.SUCI_Calc_Info."""

    priority: int = Field(ge=0, le=255)
    protection_scheme: int = Field(ge=0, le=2)
    hn_public_key_id: int | None = Field(default=None, ge=0, le=255)
    hn_public_key: str | None = None


class SIMReadResult(DomainModel):
    """Non-secret identifiers returned by a read-only card inspection."""

    reader_index: int = Field(ge=0)
    card_type: str = Field(min_length=1, max_length=100)
    atr: str = Field(pattern=r"^[0-9A-Fa-f ]+$")
    iccid: str = Field(pattern=r"^\d{18,22}$")
    imsi: str = Field(pattern=r"^\d{5,15}$")
    acc_readable: bool = False
    acc: str | None = Field(default=None, pattern=r"^[0-9A-Fa-f]{4}$")
    msisdn_readable: bool = False
    msisdn: str | None = Field(default=None, pattern=r"^\+?\d{3,15}$")
    ims_supported: bool = False
    ims_readable: bool = False
    impi: str | None = None
    impu: str | None = None
    ims_domain: str | None = None
    ist: str | None = None
    suci_supported: bool = False
    suci_readable: bool = False
    suci_usim_supported: bool = False
    suci_calculation_mode: str | None = None
    routing_indicator: str | None = None
    protection_scheme: int | None = None
    hn_public_key_id: int | None = None
    hn_public_key: str | None = None
    suci_configurations: list[SuciConfiguration] = Field(default_factory=list)
    suci_service_124_active: bool | None = None
    suci_service_125_active: bool | None = None
