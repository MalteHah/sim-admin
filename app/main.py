"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.core.dependencies import get_auth_service
from app.core.version import application_version
from app.frontend.auth import router as auth_router
from app.frontend.audit import router as audit_router
from app.frontend.backup import router as backup_router
from app.frontend.imports import router as import_router
from app.frontend.profiles import router as profiles_router
from app.frontend.provisioning import router as provisioning_router
from app.frontend.router import router as frontend_router

FRONTEND_DIRECTORY = Path(__file__).parent / "frontend"


def create_app() -> FastAPI:
    """Create and configure the web application."""
    application = FastAPI(
        title="sim-admin",
        description="Standalone SIM administration application",
        version=application_version(),
    )
    auth_service = get_auth_service()

    @application.middleware("http")
    async def require_authentication(request: Request, call_next):
        public_path = (
            request.url.path in {"/login", "/health"}
            or request.url.path.startswith("/static/")
        )
        if public_path or auth_service.verify_session(
            request.cookies.get("sim_admin_session")
        ):
            response = await call_next(request)
            if request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = "max-age=31536000"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                {"detail": "Anmeldung erforderlich"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    application.include_router(router)
    application.include_router(auth_router)
    application.include_router(audit_router)
    application.include_router(backup_router)
    application.include_router(import_router)
    application.include_router(profiles_router)
    application.include_router(provisioning_router)
    application.include_router(frontend_router)
    application.mount(
        "/static",
        StaticFiles(directory=FRONTEND_DIRECTORY / "static"),
        name="static",
    )
    return application


app = create_app()
