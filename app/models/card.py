"""Read-only card identification models."""

from pydantic import Field

from app.models.common import DomainModel


class SIMReadResult(DomainModel):
    """Non-secret identifiers returned by a read-only card inspection."""

    reader_index: int = Field(ge=0)
    card_type: str = Field(min_length=1, max_length=100)
    atr: str = Field(pattern=r"^[0-9A-Fa-f ]+$")
    iccid: str = Field(pattern=r"^\d{18,22}$")
    imsi: str = Field(pattern=r"^\d{5,15}$")
