"""Models for provisioning drafts and non-writing previews."""

from pydantic import Field, SecretStr, field_validator

from app.models.common import DomainModel


class ProvisioningDraft(DomainModel):
    """Validated input for a future SIM personalization operation."""

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
    protection_scheme: int | None = Field(default=None, ge=0, le=15)
    hn_public_key_id: int | None = Field(default=None, ge=0, le=255)
    hn_public_key: str | None = Field(default=None, pattern=r"^(?:[0-9A-Fa-f]{2})+$")

    @field_validator("ki", "opc")
    @classmethod
    def validate_hex_secret(cls, value: SecretStr) -> SecretStr:
        try:
            bytes.fromhex(value.get_secret_value())
        except ValueError as exc:
            raise ValueError("must contain hexadecimal characters") from exc
        return value


class ProvisioningStep(DomainModel):
    """One logical operation in a non-writing preview."""

    order: int = Field(ge=1)
    target: str
    action: str
    fields: list[str]
    risk: str


class ProvisioningPreview(DomainModel):
    """Redacted plan that proves no write operation was executed."""

    mode: str = "dry-run"
    write_performed: bool = False
    iccid: str
    imsi: str
    msisdn: str | None = None
    acc: str
    ki_configured: bool
    opc_configured: bool
    adm_configured: bool
    steps: list[ProvisioningStep]
    warnings: list[str]


class CardComparisonRequest(DomainModel):
    """Target identifiers for a separate read-only card comparison."""

    reader_index: int = Field(default=0, ge=0)
    target_iccid: str = Field(pattern=r"^\d{18,22}$")
    target_imsi: str = Field(pattern=r"^\d{5,15}$")


class CardComparisonResult(DomainModel):
    """Comparison between a provisioning draft and the inserted card."""

    mode: str = "read-only-comparison"
    write_performed: bool = False
    reader_index: int
    card_type: str
    atr: str
    current_iccid: str
    current_imsi: str
    target_iccid: str
    target_imsi: str
    iccid_matches: bool
    imsi_matches: bool
    warnings: list[str]


class ProfileWriteRequest(DomainModel):
    password: SecretStr = Field(min_length=1, max_length=256)
    confirmation: str = Field(pattern=r"^SIM SCHREIBEN$")
    reader_index: int = Field(default=0, ge=0)


class ProfileWriteResult(DomainModel):
    profile_id: int
    revision: int
    verified_fields: list[str]
    write_performed: bool = True
