"""Redacted views of encrypted SIM profiles."""

from datetime import date, datetime
from typing import Literal
from pydantic import Field, SecretStr, model_validator
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
    ims_configured: bool = False
    fivegs_configured: bool = False
    inventory_status: Literal["in_stock", "issued"] = "in_stock"
    issued_to: str | None = None
    issued_at: date | None = None
    inventory_note: str | None = None


class ProfileInventoryUpdateRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    status: Literal["in_stock", "issued"]
    issued_to: str | None = Field(default=None, max_length=100)
    issued_at: date | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_issuance(self):
        if self.status == "issued" and (not self.issued_to or self.issued_at is None):
            raise ValueError("Bei Ausgabe sind Name und Datum erforderlich")
        if self.status == "in_stock":
            object.__setattr__(self, "issued_to", None)
            object.__setattr__(self, "issued_at", None)
        return self


class ProfileRevisionSummary(DomainModel):
    revision: int
    created_at: datetime
    note: str


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


class ProfileAdoptReadableFieldsRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    reader_index: int = Field(default=0, ge=0)
    fields: list[Literal["impi", "impu", "ims_domain", "ist", "suci"]] = Field(min_length=1)


class ProfileAdoptReadableFieldsResult(DomainModel):
    profile_id: int
    revision: int
    adopted_fields: list[str]
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
    impi: str | None = None
    impu: str | None = None
    ims_domain: str | None = None
    ist: str | None = None
    routing_indicator: str | None = None
    protection_scheme: int | None = None
    hn_public_key_id: int | None = None
    hn_public_key: str | None = None


class ProfileChangeRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    imsi: str = Field(pattern=r"^\d{5,15}$")
    msisdn: str | None = Field(default=None, pattern=r"^\+?\d{3,15}$")
    acc: str = Field(pattern=r"^[0-9A-Fa-f]{4}$")
    ki: SecretStr | None = Field(default=None, min_length=32, max_length=32)
    opc: SecretStr | None = Field(default=None, min_length=32, max_length=32)
    impi: str | None = Field(default=None, min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+$")
    impu: str | None = Field(default=None, min_length=5, max_length=255, pattern=r"^(sip:|sips:|tel:)[^\s]+$")
    ims_domain: str | None = Field(default=None, min_length=1, max_length=253, pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
    ist: str | None = Field(default=None, pattern=r"^(?:[0-9A-Fa-f]{2})+$")
    routing_indicator: str | None = Field(default=None, pattern=r"^\d{1,4}$")
    protection_scheme: int | None = Field(default=None, ge=0, le=2)
    hn_public_key_id: int | None = Field(default=None, ge=0, le=255)
    hn_public_key: str | None = Field(default=None, pattern=r"^(?:[0-9A-Fa-f]{2})+$")

    @model_validator(mode="after")
    def validate_suci_configuration(self):
        _validate_suci_fields(self.routing_indicator, self.protection_scheme, self.hn_public_key_id, self.hn_public_key)
        return self


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
    impi: str | None = Field(default=None, min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+$")
    impu: str | None = Field(default=None, min_length=5, max_length=255, pattern=r"^(sip:|sips:|tel:)[^\s]+$")
    ims_domain: str | None = Field(default=None, min_length=1, max_length=253, pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
    ist: str | None = Field(default=None, pattern=r"^(?:[0-9A-Fa-f]{2})+$")
    routing_indicator: str | None = Field(default=None, pattern=r"^\d{1,4}$")
    protection_scheme: int | None = Field(default=None, ge=0, le=2)
    hn_public_key_id: int | None = Field(default=None, ge=0, le=255)
    hn_public_key: str | None = Field(default=None, pattern=r"^(?:[0-9A-Fa-f]{2})+$")

    @model_validator(mode="after")
    def validate_suci_configuration(self):
        _validate_suci_fields(self.routing_indicator, self.protection_scheme, self.hn_public_key_id, self.hn_public_key)
        return self


class ProfileDeleteRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    confirmation_iccid: str = Field(pattern=r"^\d{18,22}$")


def _validate_suci_fields(routing_indicator: str | None, scheme: int | None, key_id: int | None, key: str | None) -> None:
    if scheme is None:
        if key_id is not None or key: raise ValueError("Protection Scheme fehlt")
        return
    if scheme == 0:
        if key_id is not None or key: raise ValueError("Null Scheme darf keinen Schlüssel enthalten")
        if not routing_indicator: raise ValueError("SUCI Routing Indicator fehlt")
        return
    if not routing_indicator: raise ValueError("SUCI Routing Indicator fehlt")
    if key_id is None or not key: raise ValueError("Schlüssel-ID und Schlüssel fehlen")
    key_bytes = len(key) // 2
    if scheme == 1 and key_bytes != 32: raise ValueError("Scheme A benötigt 32 Schlüsselbytes")
    if scheme == 2 and key_bytes not in {33, 65}: raise ValueError("Scheme B benötigt 33 oder 65 Schlüsselbytes")
