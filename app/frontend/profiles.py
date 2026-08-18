"""Read-only encrypted profile-vault page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(include_in_schema=False)
template = Path(__file__).parent / "templates" / "profiles.html"


@router.get("/profiles", response_class=HTMLResponse)
def profiles_page() -> HTMLResponse:
    return HTMLResponse(template.read_text(encoding="utf-8"))
