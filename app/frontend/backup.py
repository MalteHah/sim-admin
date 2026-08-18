"""Encrypted backup page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

backup_file = Path(__file__).parent / "templates" / "backup.html"
router = APIRouter(include_in_schema=False)


@router.get("/backup", response_class=HTMLResponse)
def backup_page() -> HTMLResponse:
    return HTMLResponse(backup_file.read_text(encoding="utf-8"))
