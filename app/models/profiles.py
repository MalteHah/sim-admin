"""Redacted views of encrypted SIM profiles."""

from datetime import datetime
from pydantic import Field, SecretStr
from app.models.common import DomainModel


class ProfileSummary(DomainModel):
    id: int
    created_at: datetime
    iccid: str
    imsi: str
    ki_configured: bool
    opc_configured: bool
    adm_configured: bool
    revision: int = 1
    pending_change: bool = False
    card_verified: bool = False


class ProfileRevisionSummary(DomainModel):
    revision: int
    created_at: datetime


class ProfileImportResult(DomainModel):
    imported: int
    encrypted: bool = True


class ProfileRevealRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)


class ProfileAdoptCardRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    reader_index: int = Field(default=0, ge=0)


class ProfileAdoptCardResult(DomainModel):
    profile_id: int
    revision: int
    adopted_fields: list[str] = Field(default_factory=lambda: ["imsi"])
    write_performed: bool = False


class ProfileSecrets(DomainModel):
    fields: dict[str, str]


class ProfileEditableView(DomainModel):
    iccid: str
    imsi: str
    msisdn: str | None = None
    acc: str
    revision: int
    pending_change: bool = False
    changed_fields: list[str] = Field(default_factory=list)


class ProfileChangeRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    imsi: str = Field(pattern=r"^\d{5,15}$")
    msisdn: str | None = Field(default=None, pattern=r"^\+?\d{3,15}$")
    acc: str = Field(pattern=r"^[0-9A-Fa-f]{4}$")
    ki: SecretStr | None = Field(default=None, min_length=32, max_length=32)
    opc: SecretStr | None = Field(default=None, min_length=32, max_length=32)


class ProfileChangeSummary(DomainModel):
    profile_id: int
    created_at: datetime
    base_revision: int
    changed_fields: list[str]
    status: str = "pending"


class SingleProfileCreateRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    reader_index: int = Field(default=0, ge=0)
    verify_card: bool = True
    iccid: str = Field(pattern=r"^\d{18,22}$")
    imsi: str = Field(pattern=r"^\d{5,15}$")
    msisdn: str | None = Field(default=None, pattern=r"^\+?\d{3,15}$")
    acc: str = Field(default="0001", pattern=r"^[0-9A-Fa-f]{4}$")
    ki: SecretStr = Field(min_length=32, max_length=32)
    opc: SecretStr = Field(min_length=32, max_length=32)
    adm: SecretStr = Field(min_length=4, max_length=32)


class ProfileDeleteRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    confirmation_iccid: str = Field(pattern=r"^\d{18,22}$")
