"""Models for non-persistent CSV import previews."""

from pydantic import Field, SecretStr

from app.models.common import DomainModel


class CSVImportRequest(DomainModel):
    content: SecretStr = Field(max_length=2_000_000)


class CSVImportRow(DomainModel):
    row_number: int
    iccid: str
    imsi: str
    valid: bool
    errors: list[str]
    ki_configured: bool
    opc_configured: bool
    adm_configured: bool


class CSVImportPreview(DomainModel):
    mode: str = "preview"
    stored: bool = False
    write_performed: bool = False
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[CSVImportRow]
