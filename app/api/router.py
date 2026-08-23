"""Initial HTTP routes."""

from typing import Annotated
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.adapters.readers import ReaderAdapterError
from app.adapters.sim_cards import SIMReadError, SIMWriteError
from app.core.auth import AuthService
from app.core.dependencies import (
    get_card_comparison_service,
    get_auth_service,
    get_audit_service,
    get_backup_service,
    get_csv_import_service,
    get_profile_vault_service,
    get_profile_write_service,
    get_provisioning_preview_service,
    get_reader_service,
    get_sim_card_service,
)
from app.models import (
    CardComparisonRequest,
    CardComparisonResult,
    AuditEvent,
    BackupRequest,
    BackupFile,
    BackupInspectRequest,
    BackupInspection,
    BackupRestoreRequest,
    BackupResult,
    BackupTarget,
    CSVImportPreview,
    CSVImportRequest,
    ProfileImportResult,
    ProfileInventoryUpdateRequest,
    ProfileAdoptCardRequest,
    ProfileAdoptCardResult,
    ProfileAdoptReadableFieldsRequest,
    ProfileAdoptReadableFieldsResult,
    ProfileSummary,
    ProfileRevealRequest,
    ProfileRevisionSummary,
    ProfileSecrets,
    ProfileChangeRequest,
    ProfileChangeSummary,
    ProfileEditableView,
    ProfileDeleteRequest,
    ProfileWriteRequest,
    ProfileWriteResult,
    ProvisioningDraft,
    ProvisioningPreview,
    Reader,
    SIMReadResult,
    SingleProfileCreateRequest,
)
from app.services.provisioning import CardComparisonService, ProfileWriteService, ProvisioningPreviewService
from app.services.audit import AuditService
from app.services.backup import BackupError, BackupService
from app.services.imports import CSVImportError, CSVImportPreviewService
from app.services.profiles import ProfileVaultService
from app.services.readers import ReaderService
from app.services.sim_cards import SIMCardService
from app.core.version import application_version

router = APIRouter()


@router.get("/api/v1")
def api_information() -> dict[str, str]:
    """Return basic API information."""
    return {"application": "sim-admin", "version": application_version()}


@router.get("/health")
def health() -> dict[str, str]:
    """Expose a basic process health check."""
    return {"status": "ok"}


@router.get("/api/v1/readers", response_model=list[Reader])
def list_readers(
    service: Annotated[ReaderService, Depends(get_reader_service)],
) -> list[Reader]:
    """List connected PC/SC readers without accessing SIM contents."""
    try:
        return service.list_readers()
    except ReaderAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/api/v1/sim/read", response_model=SIMReadResult)
def read_sim_identity(
    service: Annotated[SIMCardService, Depends(get_sim_card_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    reader_index: int = 0,
) -> SIMReadResult:
    """Read ICCID and IMSI without modifying the selected SIM."""
    try:
        result = service.read_identity(reader_index)
        audit.record("sim.read", "success")
        return result
    except SIMReadError as exc:
        audit.record("sim.read", "error", exc.code)
        error_status = (
            status.HTTP_409_CONFLICT
            if exc.code == "no_card"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(
            status_code=error_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.post("/api/v1/provisioning/preview", response_model=ProvisioningPreview)
def preview_provisioning(
    draft: ProvisioningDraft,
    service: Annotated[
        ProvisioningPreviewService, Depends(get_provisioning_preview_service)
    ],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> ProvisioningPreview:
    """Validate a draft and return a redacted plan without card access."""
    preview = service.create_preview(draft)
    audit.record("provisioning.preview", "success", "dry-run")
    return preview


@router.post(
    "/api/v1/provisioning/card-comparison",
    response_model=CardComparisonResult,
)
def compare_provisioning_to_card(
    request: CardComparisonRequest,
    service: Annotated[CardComparisonService, Depends(get_card_comparison_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> CardComparisonResult:
    """Compare target identifiers to the inserted card without modifying it."""
    try:
        result = service.compare(request)
        comparison = (
            "match" if result.iccid_matches and result.imsi_matches else "difference"
        )
        audit.record("provisioning.card_comparison", "success", comparison)
        return result
    except SIMReadError as exc:
        audit.record("provisioning.card_comparison", "error", exc.code)
        error_status = (
            status.HTTP_409_CONFLICT
            if exc.code == "no_card"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(
            status_code=error_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/api/v1/audit", response_model=list[AuditEvent])
def list_audit_events(
    audit: Annotated[AuditService, Depends(get_audit_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEvent]:
    """Return recent metadata-only activity records."""
    return audit.list_recent(limit)


@router.get("/api/v1/backups/targets", response_model=list[BackupTarget])
def list_backup_targets(
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> list[BackupTarget]:
    """List mounted removable-media backup destinations."""
    return service.list_targets()


@router.post("/api/v1/backups", response_model=BackupResult)
def create_backup(
    request: BackupRequest,
    service: Annotated[BackupService, Depends(get_backup_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> BackupResult:
    """Create an encrypted, verified backup on an approved target."""
    try:
        result = service.create(request.target_path, request.password.get_secret_value())
    except BackupError as exc:
        audit.record("backup.create", "error", exc.code)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    audit.record("backup.create", "success", "encrypted_verified")
    return result


@router.get("/api/v1/backups", response_model=list[BackupFile])
def list_backups(service: Annotated[BackupService, Depends(get_backup_service)]) -> list[BackupFile]:
    return service.list_files()


def _backup_error(exc: BackupError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": exc.code, "message": str(exc)})


@router.post("/api/v1/backups/inspect", response_model=BackupInspection)
def inspect_backup(request: BackupInspectRequest, service: Annotated[BackupService, Depends(get_backup_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> BackupInspection:
    try:
        result = service.inspect(request.target_path, request.filename, request.password.get_secret_value())
    except BackupError as exc:
        audit.record("backup.inspect", "error", exc.code)
        raise _backup_error(exc) from exc
    audit.record("backup.inspect", "success", "integrity_valid")
    return result


@router.post("/api/v1/backups/restore", response_model=BackupInspection)
def restore_backup(request: BackupRestoreRequest, service: Annotated[BackupService, Depends(get_backup_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> BackupInspection:
    try:
        result = service.restore(request.target_path, request.filename, request.password.get_secret_value(), request.confirmation)
    except BackupError as exc:
        audit.record("backup.restore", "error", exc.code)
        raise _backup_error(exc) from exc
    audit.record("backup.restore", "success", "integrity_valid")
    return result


@router.post("/api/v1/imports/csv/preview", response_model=CSVImportPreview)
def preview_csv_import(request: CSVImportRequest, service: Annotated[CSVImportPreviewService, Depends(get_csv_import_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> CSVImportPreview:
    try:
        result = service.create_preview(request.content.get_secret_value())
    except CSVImportError as exc:
        audit.record("import.csv_preview", "error", exc.code)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": exc.code, "message": str(exc)}) from exc
    audit.record("import.csv_preview", "success", "valid" if result.invalid_rows == 0 else "validation_errors")
    return result


@router.post("/api/v1/profiles/import", response_model=ProfileImportResult)
def import_profiles(request: CSVImportRequest, service: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileImportResult:
    try:
        result = service.import_csv(request.content.get_secret_value())
    except CSVImportError as exc:
        audit.record("profiles.import", "error", exc.code)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": exc.code, "message": str(exc)}) from exc
    audit.record("profiles.import", "success", "encrypted")
    return result


@router.get("/api/v1/profiles", response_model=list[ProfileSummary])
def list_profiles(service: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> list[ProfileSummary]:
    return service.list_profiles()


@router.get("/api/v1/profiles/by-iccid/{iccid}", response_model=ProfileSummary | None)
def find_profile_by_iccid(iccid: str, service: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> ProfileSummary | None:
    return service.find_by_iccid(iccid)


@router.post("/api/v1/profiles/{profile_id}/inventory", response_model=ProfileSummary)
def update_profile_inventory(profile_id: int, payload: ProfileInventoryUpdateRequest, request: Request,
    vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileSummary:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.inventory_update", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try:
        vault.set_inventory(profile_id, payload.status, payload.issued_to,
            payload.issued_at.isoformat() if payload.issued_at else None, payload.note)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    audit.record("profiles.inventory_update", "success", f"inventory_{payload.status}")
    return next(profile for profile in vault.list_profiles() if profile.id == profile_id)


@router.post("/api/v1/profiles/single", response_model=ProfileSummary, status_code=status.HTTP_201_CREATED)
def create_single_profile(payload: SingleProfileCreateRequest, request: Request, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], cards: Annotated[SIMCardService, Depends(get_sim_card_service)], auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileSummary:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.single_create", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    if payload.verify_card:
        try: identity = cards.read_identity(payload.reader_index)
        except SIMReadError as exc:
            audit.record("profiles.single_create", "error", exc.code)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": exc.code, "message": str(exc)}) from exc
        if identity.iccid != payload.iccid or identity.imsi != payload.imsi:
            audit.record("profiles.single_create", "error", "card_changed")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Die eingelegte Karte hat sich seit dem Einlesen geändert")
    draft = ProvisioningDraft(iccid=payload.iccid, imsi=payload.imsi, msisdn=payload.msisdn, acc=payload.acc,
        ki=payload.ki, opc=payload.opc, adm=payload.adm, impi=payload.impi, impu=payload.impu,
        ims_domain=payload.ims_domain, ist=payload.ist, routing_indicator=payload.routing_indicator,
        protection_scheme=payload.protection_scheme, hn_public_key_id=payload.hn_public_key_id,
        hn_public_key=payload.hn_public_key)
    try: result = vault.add_profile(draft, card_verified=payload.verify_card)
    except ValueError as exc:
        if str(exc) == "duplicate_iccid":
            audit.record("profiles.single_create", "error", "duplicate_iccid")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Diese ICCID ist bereits im Profiltresor vorhanden") from exc
        raise
    audit.record("profiles.single_create", "success", "encrypted_revision_1_verified" if payload.verify_card else "encrypted_revision_1_pending_card")
    return result


@router.post("/api/v1/profiles/{profile_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, payload: ProfileDeleteRequest, request: Request, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> Response:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.delete", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try: vault.delete_profile(profile_id, payload.confirmation_iccid)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    except ValueError as exc:
        audit.record("profiles.delete", "error", "confirmation_mismatch")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Die eingegebene ICCID stimmt nicht überein") from exc
    audit.record("profiles.delete", "success", "profile_revisions_and_draft")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/profiles/{profile_id}/revisions", response_model=list[ProfileRevisionSummary])
def list_profile_revisions(profile_id: int, service: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> list[ProfileRevisionSummary]:
    try: return service.list_revisions(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc


@router.get("/api/v1/profiles/{profile_id}/editable", response_model=ProfileEditableView)
def get_editable_profile(profile_id: int, service: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> ProfileEditableView:
    try: return service.get_editable(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc


@router.get("/api/v1/profiles/{profile_id}/change-draft", response_model=ProfileChangeSummary | None)
def get_profile_change_draft(profile_id: int, service: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> ProfileChangeSummary | None:
    return service.get_change_summary(profile_id)


@router.post("/api/v1/profiles/{profile_id}/change-draft", response_model=ProfileChangeSummary)
def prepare_profile_change(profile_id: int, payload: ProfileChangeRequest, request: Request, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileChangeSummary:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.change_draft", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try:
        result = vault.prepare_change(profile_id, payload.imsi, payload.msisdn, payload.acc,
            payload.ki.get_secret_value() if payload.ki else None, payload.opc.get_secret_value() if payload.opc else None,
            payload.impi, payload.impu, payload.ims_domain, payload.ist, payload.routing_indicator,
            payload.protection_scheme, payload.hn_public_key_id, payload.hn_public_key)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    except ValueError as exc:
        if str(exc) == "no_changes": raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Es wurden keine Änderungen eingegeben") from exc
        raise
    audit.record("profiles.change_draft", "success", "encrypted_pending")
    return result


@router.post("/api/v1/profiles/{profile_id}/change-draft/discard", status_code=status.HTTP_204_NO_CONTENT)
def discard_profile_change(profile_id: int, payload: ProfileRevealRequest, request: Request, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> Response:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.change_draft_discard", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try: discarded = vault.discard_change(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    if not discarded: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Änderungsentwurf vorhanden")
    audit.record("profiles.change_draft_discard", "success", "discarded")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/v1/profiles/{profile_id}/change-draft/preview", response_model=ProvisioningPreview)
def preview_profile_change(profile_id: int, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], preview_service: Annotated[ProvisioningPreviewService, Depends(get_provisioning_preview_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProvisioningPreview:
    try: draft = vault.get_change_draft(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Änderungsentwurf vorhanden") from exc
    result = preview_service.create_preview(draft)
    audit.record("profiles.change_draft_preview", "success", "dry-run")
    return result


@router.post("/api/v1/profiles/{profile_id}/change-draft/card-comparison", response_model=CardComparisonResult)
def compare_profile_change_to_card(profile_id: int, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], comparison: Annotated[CardComparisonService, Depends(get_card_comparison_service)], audit: Annotated[AuditService, Depends(get_audit_service)], reader_index: int = 0) -> CardComparisonResult:
    try: draft = vault.get_change_draft(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Änderungsentwurf vorhanden") from exc
    try:
        result = comparison.compare(CardComparisonRequest(reader_index=reader_index, target_iccid=draft.iccid, target_imsi=draft.imsi,
            compare_standard_fields=True, target_acc=draft.acc, target_msisdn=draft.msisdn,
            compare_ims=True, target_impi=draft.impi, target_impu=draft.impu, target_ims_domain=draft.ims_domain, target_ist=draft.ist,
            compare_suci=True, target_routing_indicator=draft.routing_indicator, target_protection_scheme=draft.protection_scheme,
            target_hn_public_key_id=draft.hn_public_key_id, target_hn_public_key=draft.hn_public_key))
    except SIMReadError as exc:
        audit.record("profiles.change_draft_card_comparison", "error", exc.code)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if exc.code == "no_card" else status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": exc.code, "message": str(exc)}) from exc
    if result.iccid_matches: vault.mark_card_verified(profile_id)
    audit.record("profiles.change_draft_card_comparison", "success", "match" if result.iccid_matches and result.imsi_matches else "difference")
    return result


@router.post("/api/v1/profiles/{profile_id}/change-draft/write", response_model=ProfileWriteResult)
def write_profile_change(profile_id: int, payload: ProfileWriteRequest, request: Request, service: Annotated[ProfileWriteService, Depends(get_profile_write_service)], auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileWriteResult:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.change_draft_write", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try:
        revision, verified = service.execute(profile_id, payload.reader_index)
    except KeyError as exc:
        audit.record("profiles.change_draft_write", "error", "missing_draft")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Änderungsentwurf vorhanden") from exc
    except SIMWriteError as exc:
        audit.record("profiles.change_draft_write", "error", exc.code)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": exc.code, "message": str(exc)}) from exc
    except ValueError as exc:
        code = str(exc); audit.record("profiles.change_draft_write", "error", code)
        message = "Der Entwurf enthält für diesen Kartentyp nicht unterstützte Felder" if code == "unsupported_fields" else "Schreibvorgang konnte nicht vollständig bestätigt werden"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": message}) from exc
    audit.record("profiles.change_draft_write", "success", f"revision_{revision}")
    return ProfileWriteResult(profile_id=profile_id, revision=revision, verified_fields=verified)


@router.post("/api/v1/profiles/{profile_id}/preview", response_model=ProvisioningPreview)
def preview_stored_profile(profile_id: int, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], preview_service: Annotated[ProvisioningPreviewService, Depends(get_provisioning_preview_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProvisioningPreview:
    try: draft = vault.get_draft(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    result = preview_service.create_preview(draft)
    audit.record("profiles.preview", "success", "dry-run")
    return result


@router.post("/api/v1/profiles/{profile_id}/card-comparison", response_model=CardComparisonResult)
def compare_stored_profile(profile_id: int, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], comparison: Annotated[CardComparisonService, Depends(get_card_comparison_service)], audit: Annotated[AuditService, Depends(get_audit_service)], reader_index: int = 0) -> CardComparisonResult:
    try: draft = vault.get_draft(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    try:
        result = comparison.compare(CardComparisonRequest(reader_index=reader_index, target_iccid=draft.iccid, target_imsi=draft.imsi,
            compare_ims=True, target_impi=draft.impi, target_impu=draft.impu, target_ims_domain=draft.ims_domain, target_ist=draft.ist,
            compare_suci=True, target_routing_indicator=draft.routing_indicator, target_protection_scheme=draft.protection_scheme,
            target_hn_public_key_id=draft.hn_public_key_id, target_hn_public_key=draft.hn_public_key))
    except SIMReadError as exc:
        audit.record("profiles.card_comparison", "error", exc.code)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if exc.code == "no_card" else status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": exc.code, "message": str(exc)}) from exc
    if result.iccid_matches: vault.mark_card_verified(profile_id)
    audit.record("profiles.card_comparison", "success", "match" if result.iccid_matches and result.imsi_matches else "difference")
    return result


@router.post("/api/v1/profiles/{profile_id}/adopt-card", response_model=ProfileAdoptCardResult)
def adopt_card_data(profile_id: int, payload: ProfileAdoptCardRequest, request: Request,
    vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)],
    cards: Annotated[SIMCardService, Depends(get_sim_card_service)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileAdoptCardResult:
    """Adopt the re-read card IMSI into the vault without writing to the SIM."""
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.adopt_card", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try:
        identity = cards.read_identity(payload.reader_index)
        revision = vault.adopt_card_imsi(profile_id, identity.iccid, identity.imsi)
    except SIMReadError as exc:
        audit.record("profiles.adopt_card", "error", exc.code)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if exc.code == "no_card" else status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": str(exc)}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    except ValueError as exc:
        code = str(exc)
        messages = {
            "iccid_mismatch": "Die eingelegte Karte gehört nicht zu diesem Profil.",
            "pending_change": "Vor der Übernahme muss der vorhandene Änderungsentwurf abgeschlossen oder verworfen werden.",
            "no_changes": "Die IMSI der Karte entspricht bereits dem Profil.",
        }
        audit.record("profiles.adopt_card", "error", code)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": messages.get(code, "Kartendaten konnten nicht übernommen werden.")}) from exc
    audit.record("profiles.adopt_card", "success", f"revision_{revision}")
    return ProfileAdoptCardResult(profile_id=profile_id, revision=revision)


@router.post("/api/v1/profiles/{profile_id}/adopt-readable-fields", response_model=ProfileAdoptReadableFieldsResult)
def adopt_readable_card_fields(profile_id: int, payload: ProfileAdoptReadableFieldsRequest, request: Request,
    vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)],
    cards: Annotated[SIMCardService, Depends(get_sim_card_service)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileAdoptReadableFieldsResult:
    """Adopt selected non-secret IMS/SUCI values after a fresh card read."""
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.adopt_readable_fields", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try:
        identity = cards.read_identity(payload.reader_index)
        if any(field in payload.fields for field in ("impi", "impu", "ims_domain", "ist")) and not identity.ims_readable:
            raise ValueError("ims_unreadable")
        if "suci" in payload.fields and not identity.suci_readable:
            raise ValueError("suci_unreadable")
        if "acc" in payload.fields and not identity.acc_readable:
            raise ValueError("acc_unreadable")
        if "msisdn" in payload.fields and not identity.msisdn_readable:
            raise ValueError("msisdn_unreadable")
        values = {"acc": identity.acc, "msisdn": identity.msisdn,
            "impi": identity.impi, "impu": identity.impu, "ims_domain": identity.ims_domain, "ist": identity.ist,
            "routing_indicator": identity.routing_indicator, "protection_scheme": identity.protection_scheme,
            "hn_public_key_id": identity.hn_public_key_id, "hn_public_key": identity.hn_public_key}
        revision, adopted = vault.adopt_readable_card_fields(profile_id, identity.iccid, values, payload.fields)
    except SIMReadError as exc:
        audit.record("profiles.adopt_readable_fields", "error", exc.code)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": exc.code, "message": str(exc)}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    except ValueError as exc:
        code = str(exc); messages = {"iccid_mismatch": "Die eingelegte Karte gehört nicht zu diesem Profil.",
            "pending_change": "Vor der Übernahme muss der vorhandene Änderungsentwurf abgeschlossen oder verworfen werden.",
            "no_changes": "Die ausgewählten Kartendaten entsprechen bereits dem Profil.",
            "acc_unreadable": "Der ACC konnte nicht erneut gelesen werden.",
            "msisdn_unreadable": "Die MSISDN konnte nicht erneut gelesen werden.",
            "ims_unreadable": "Die IMS-Daten konnten nicht erneut gelesen werden.", "suci_unreadable": "Die SUCI-Daten konnten nicht erneut gelesen werden."}
        audit.record("profiles.adopt_readable_fields", "error", code)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": messages.get(code, "Kartendaten konnten nicht übernommen werden.")}) from exc
    audit.record("profiles.adopt_readable_fields", "success", f"revision_{revision}")
    return ProfileAdoptReadableFieldsResult(profile_id=profile_id, revision=revision, adopted_fields=adopted)


@router.post("/api/v1/profiles/{profile_id}/secrets", response_model=ProfileSecrets)
def reveal_profile_secrets(profile_id: int, payload: ProfileRevealRequest, request: Request, response: Response, vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> ProfileSecrets:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, payload.password.get_secret_value(), client):
        audit.record("profiles.reveal", "error", "reauthentication_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")
    try: fields = vault.get_secrets(profile_id)
    except KeyError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nicht gefunden") from exc
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    audit.record("profiles.reveal", "success", "reauthenticated")
    return ProfileSecrets(fields=fields)


@router.get("/api/v1/profiles/export")
def export_profile_inventory(vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)], audit: Annotated[AuditService, Depends(get_audit_service)]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(["ICCID", "IMSI", "Bestandsstatus", "Ausgegeben an", "Ausgabedatum", "Bemerkung", "Ki vorhanden", "OPc vorhanden", "ADM1 vorhanden"])
    for profile in vault.list_profiles():
        writer.writerow([profile.iccid, profile.imsi, "ausgegeben" if profile.inventory_status == "issued" else "im Bestand",
            profile.issued_to or "", profile.issued_at.isoformat() if profile.issued_at else "", profile.inventory_note or "",
            "ja" if profile.ki_configured else "nein", "ja" if profile.opc_configured else "nein", "ja" if profile.adm_configured else "nein"])
    audit.record("profiles.inventory_export", "success", "redacted")
    return Response(content="\ufeff" + buffer.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=sim-admin-inventar.csv", "Cache-Control": "no-store, max-age=0"})
