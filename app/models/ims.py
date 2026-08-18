"""IP Multimedia Subsystem domain model."""

from pydantic import Field

from app.models.common import DomainModel


class IMSProfile(DomainModel):
    """IMS identities and service-table data for a subscription."""

    impi: str = Field(min_length=1, max_length=255)
    impu: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=253)
    ist: str | None = Field(
        default=None,
        pattern=r"^[0-9A-Fa-f]+$",
        description="IMS Service Table encoded as hexadecimal characters",
    )
