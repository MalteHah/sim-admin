from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(include_in_schema=False)
template = Path(__file__).parent / "templates" / "import.html"


@router.get("/import", response_class=HTMLResponse)
def import_page() -> HTMLResponse:
    return HTMLResponse(template.read_text(encoding="utf-8"))
