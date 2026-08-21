"""Login and logout routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.auth import AuthService, PasswordChangeError
from app.core.dependencies import get_audit_service, get_auth_service, get_profile_vault_service
from app.models import SuciKeyDeleteRequest, SuciKeyImportRequest, SuciKeyStatusRequest, SuciKeySummary
from app.services.audit import AuditService
from app.services.profiles import ProfileVaultService

login_file = Path(__file__).parent / "templates" / "login.html"
settings_file = Path(__file__).parent / "templates" / "settings.html"
router = APIRouter(include_in_schema=False)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


@router.get("/login", response_class=HTMLResponse)
def login_page(
    service: Annotated[AuthService, Depends(get_auth_service)],
    sim_admin_session: Annotated[str | None, Cookie()] = None,
) -> Response:
    if service.verify_session(sim_admin_session):
        return Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
    return HTMLResponse(login_file.read_text(encoding="utf-8"))


@router.post("/login")
def login(
    credentials: LoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Response:
    client = request.client.host if request.client else "unknown"
    if not service.verify_login(credentials.username, credentials.password, client):
        audit.record("auth.login", "error", "invalid_credentials", username="unknown")
        return JSONResponse(
            {"detail": "Benutzername oder Passwort ist falsch"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    audit.record("auth.login", "success")
    response = JSONResponse({"status": "ok"})
    response.set_cookie(
        "sim_admin_session",
        service.create_session(),
        httponly=True,
        max_age=8 * 60 * 60,
        samesite="strict",
        secure=service.secure_cookie,
        path="/",
    )
    return response


@router.post("/logout")
def logout(audit: Annotated[AuditService, Depends(get_audit_service)]) -> Response:
    audit.record("auth.logout", "success")
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie("sim_admin_session", path="/")
    return response


@router.get("/settings", response_class=HTMLResponse)
def settings_page() -> HTMLResponse:
    return HTMLResponse(settings_file.read_text(encoding="utf-8"))


@router.post("/api/v1/settings/password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Response:
    client = request.client.host if request.client else "unknown"
    try:
        service.change_password(payload.current_password, payload.new_password, client)
    except PasswordChangeError as exc:
        audit.record("auth.password_change", "error", exc.code)
        status_code = (
            status.HTTP_401_UNAUTHORIZED
            if exc.code == "invalid_password"
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            {"detail": {"code": exc.code, "message": str(exc)}},
            status_code=status_code,
        )
    audit.record("auth.password_change", "success")
    return JSONResponse({"status": "ok"})


@router.get("/api/v1/settings/suci-keys", response_model=list[SuciKeySummary])
def list_suci_keys(vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> list[SuciKeySummary]:
    return vault.list_suci_keys()


def _verify_settings_password(password: str, request: Request, auth: AuthService, audit: AuditService, action: str) -> None:
    client = request.client.host if request.client else "unknown"
    if not auth.verify_login(auth.username, password, client):
        audit.record(action, "error", "reauthentication_failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passwort ist falsch")


@router.post("/api/v1/settings/suci-keys", response_model=SuciKeySummary, status_code=status.HTTP_201_CREATED)
def import_suci_key(payload: SuciKeyImportRequest, request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> SuciKeySummary:
    _verify_settings_password(payload.password.get_secret_value(), request, auth, audit, "settings.suci_key_import")
    try:
        result = vault.import_suci_key(payload.name, payload.scheme, payload.key_id, payload.key_data)
    except ValueError as exc:
        messages = {"duplicate_key_id": "Diese Key ID ist für das Schutzverfahren bereits vorhanden",
            "duplicate_key": "Dieser öffentliche Schlüssel ist bereits vorhanden"}
        detail = messages.get(str(exc), str(exc))
        audit.record("settings.suci_key_import", "error", str(exc) if str(exc) in messages else "invalid_public_key")
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    audit.record("settings.suci_key_import", "success", f"scheme_{payload.scheme}")
    return result


@router.patch("/api/v1/settings/suci-keys/{key_db_id}", response_model=SuciKeySummary)
def change_suci_key_status(key_db_id: int, payload: SuciKeyStatusRequest, request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)],
    vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> SuciKeySummary:
    _verify_settings_password(payload.password.get_secret_value(), request, auth, audit, "settings.suci_key_status")
    try: result = vault.set_suci_key_active(key_db_id, payload.active)
    except KeyError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schlüsselprofil nicht gefunden") from exc
    audit.record("settings.suci_key_status", "success", "activated" if payload.active else "deactivated")
    return result


@router.delete("/api/v1/settings/suci-keys/{key_db_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_suci_key(key_db_id: int, payload: SuciKeyDeleteRequest, request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)], audit: Annotated[AuditService, Depends(get_audit_service)],
    vault: Annotated[ProfileVaultService, Depends(get_profile_vault_service)]) -> Response:
    _verify_settings_password(payload.password.get_secret_value(), request, auth, audit, "settings.suci_key_delete")
    try: vault.delete_suci_key(key_db_id)
    except KeyError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schlüsselprofil nicht gefunden") from exc
    except ValueError as exc:
        audit.record("settings.suci_key_delete", "error", "key_in_use")
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Der Schlüssel wird von einem Profil oder einer Revision verwendet") from exc
    audit.record("settings.suci_key_delete", "success", "unused_key")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
