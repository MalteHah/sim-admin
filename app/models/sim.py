"""SIM subscription domain model."""

from pydantic import Field, SecretStr

from app.models.common import DomainModel


class SIMProfile(DomainModel):
    """Card and subscriber data independent of pySim's data structures."""

    iccid: str = Field(pattern=r"^\d{18,22}$")
    imsi: str = Field(pattern=r"^\d{5,15}$")
    msisdn: str | None = Field(default=None, pattern=r"^\+?\d{3,15}$")
    acc: str | None = Field(default=None, pattern=r"^[0-9A-Fa-f]{4}$")
    pin: SecretStr | None = Field(default=None, min_length=4, max_length=8)
    puk: SecretStr | None = Field(default=None, min_length=8, max_length=8)
    ki: SecretStr | None = Field(default=None, min_length=32, max_length=32)
    opc: SecretStr | None = Field(default=None, min_length=32, max_length=32)
    adm: SecretStr | None = Field(default=None, min_length=4, max_length=32)
