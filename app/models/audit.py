"""Safe audit-event response models."""

from datetime import datetime

from app.models.common import DomainModel


class AuditEvent(DomainModel):
    """Metadata-only audit record; never contains subscriber values."""

    id: int
    created_at: datetime
    username: str
    action: str
    status: str
    detail: str | None = None
