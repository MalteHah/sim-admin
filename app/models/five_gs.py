"""5G System domain models."""

from datetime import datetime
from pydantic import Field, SecretStr

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


class SuciKeySummary(DomainModel):
    id: int
    created_at: datetime
    name: str
    scheme: int
    key_id: int
    public_key: str
    fingerprint: str
    active: bool
    in_use: bool


class SuciKeyImportRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=100)
    scheme: int = Field(ge=1, le=2)
    key_id: int = Field(ge=1, le=255)
    key_data: str = Field(min_length=1, max_length=8192)


class SuciKeyStatusRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    active: bool


class SuciKeyDeleteRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
