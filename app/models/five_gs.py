"""5G System domain models."""

from pydantic import Field

from app.models.common import DomainModel


class HomeNetworkPublicKey(DomainModel):
    """A home-network public key used for SUCI concealment."""

    identifier: int = Field(ge=0, le=255)
    value: str = Field(min_length=1, pattern=r"^[0-9A-Fa-f]+$")


class FiveGSProfile(DomainModel):
    """5GS parameters associated with a subscription."""

    suci: str | None = Field(default=None, max_length=255)
    routing_indicator: str = Field(pattern=r"^\d{1,4}$")
    protection_scheme: int = Field(ge=0, le=15)
    public_keys: list[HomeNetworkPublicKey] = Field(default_factory=list)
