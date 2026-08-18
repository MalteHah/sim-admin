"""Smart-card reader domain model."""

from enum import StrEnum

from pydantic import Field

from app.models.common import DomainModel


class ReaderStatus(StrEnum):
    """Current availability of a smart-card reader."""

    DISCONNECTED = "disconnected"
    READY = "ready"
    CARD_PRESENT = "card_present"
    ERROR = "error"


class Reader(DomainModel):
    """A reader discovered by a future hardware adapter."""

    name: str = Field(min_length=1, max_length=255)
    reader_type: str | None = Field(default=None, max_length=100)
    status: ReaderStatus = ReaderStatus.DISCONNECTED
    atr: str | None = Field(
        default=None,
        pattern=r"^[0-9A-Fa-f ]+$",
        description="Answer To Reset as hexadecimal bytes",
    )
