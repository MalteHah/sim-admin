"""Provisioning draft page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

provisioning_file = Path(__file__).parent / "templates" / "provisioning.html"
router = APIRouter(include_in_schema=False)


@router.get("/provisioning", response_class=HTMLResponse)
def provisioning_page() -> HTMLResponse:
    return HTMLResponse(provisioning_file.read_text(encoding="utf-8"))
