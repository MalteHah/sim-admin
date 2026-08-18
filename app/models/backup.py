"""Models for encrypted backups on removable media."""

from pydantic import Field, SecretStr

from app.models.common import DomainModel


class BackupTarget(DomainModel):
    path: str
    name: str
    free_bytes: int


class BackupRequest(DomainModel):
    target_path: str
    password: SecretStr = Field(min_length=12, max_length=256)


class BackupResult(DomainModel):
    filename: str
    size_bytes: int
    verified: bool
    encrypted: bool = True


class BackupFile(DomainModel):
    target_path: str
    filename: str
    size_bytes: int


class BackupInspectRequest(DomainModel):
    target_path: str
    filename: str
    password: SecretStr = Field(min_length=12, max_length=256)


class BackupInspection(DomainModel):
    filename: str
    created_at: str
    format_version: int
    contents: list[str]
    integrity_valid: bool


class BackupRestoreRequest(BackupInspectRequest):
    confirmation: str
