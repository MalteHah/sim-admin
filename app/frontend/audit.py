"""Activity-log page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

activity_file = Path(__file__).parent / "templates" / "activity.html"
router = APIRouter(include_in_schema=False)


@router.get("/activity", response_class=HTMLResponse)
def activity_page() -> HTMLResponse:
    return HTMLResponse(activity_file.read_text(encoding="utf-8"))
