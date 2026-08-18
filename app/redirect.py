"""Minimal HTTP-to-HTTPS redirect application."""

import os

import os

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/{path:path}")
def redirect_to_https(request: Request, path: str) -> RedirectResponse:
    """Redirect legacy HTTP bookmarks without accepting credentials."""
    port = int(os.getenv("SIM_ADMIN_HTTPS_PORT", "8443"))
    hostname = os.getenv("SIM_ADMIN_HTTPS_HOST") or request.url.hostname or "localhost"
    target = f"https://{hostname}:{port}/{path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(target, status_code=308)
