"""Application dependency construction."""

from functools import lru_cache

from app.adapters.pcsc import PcscReaderAdapter
from app.adapters.pysim import PySimCardAdapter
from app.core.auth import AuthService, AuthSettings
from app.services.readers import ReaderService
from app.services.provisioning import CardComparisonService, ProfileWriteService, ProvisioningPreviewService
from app.services.audit import AuditService
from app.services.backup import BackupService
from app.services.imports import CSVImportPreviewService
from app.services.profiles import ProfileVaultService
from app.services.sim_cards import SIMCardService


@lru_cache
def get_auth_service() -> AuthService:
    """Return the process-wide authentication service."""
    return AuthService(AuthSettings.from_environment())


@lru_cache
def get_audit_service() -> AuditService:
    """Return the process-wide metadata-only audit service."""
    return AuditService()


@lru_cache
def get_backup_service() -> BackupService:
    """Return the encrypted removable-media backup service."""
    return BackupService(get_audit_service(), profiles=get_profile_vault_service())


@lru_cache
def get_csv_import_service() -> CSVImportPreviewService:
    return CSVImportPreviewService()


@lru_cache
def get_profile_vault_service() -> ProfileVaultService:
    return ProfileVaultService()


@lru_cache
def get_reader_service() -> ReaderService:
    """Return the process-wide reader service."""
    return ReaderService(PcscReaderAdapter())


@lru_cache
def get_sim_card_service() -> SIMCardService:
    """Return the process-wide read-only SIM service."""
    return SIMCardService(PySimCardAdapter())


@lru_cache
def get_provisioning_preview_service() -> ProvisioningPreviewService:
    """Return the planner, which deliberately has no card adapter."""
    return ProvisioningPreviewService()


@lru_cache
def get_card_comparison_service() -> CardComparisonService:
    """Return the read-only card comparison service."""
    return CardComparisonService(PySimCardAdapter())


@lru_cache
def get_profile_write_service() -> ProfileWriteService:
    return ProfileWriteService(PySimCardAdapter(timeout_seconds=30), get_profile_vault_service())
