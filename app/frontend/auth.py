"""Login and logout routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.auth import AuthService, PasswordChangeError
from app.core.dependencies import get_audit_service, get_auth_service
from app.services.audit import AuditService

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
