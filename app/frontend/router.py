"""Routes for the standalone web interface."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.core.version import application_version

dashboard_file = Path(__file__).parent / "templates" / "dashboard.html"
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """Render the local administration dashboard."""
    content = dashboard_file.read_text(encoding="utf-8").replace("{{VERSION}}", application_version())
    return HTMLResponse(content)
