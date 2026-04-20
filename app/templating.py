from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .auth import ensure_csrf
from .db import SessionLocal
from .models import User
from .settings import settings

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render(request: Request, name: str, **context) -> "templates.TemplateResponse":
    user = context.pop("user", None)
    if user is None:
        uid = request.session.get("user_id") if hasattr(request, "session") else None
        if uid:
            with SessionLocal() as db:
                user = db.query(User).filter(User.id == uid).one_or_none()

    ctx = {
        "base_url": settings.base_url,
        "csrf_token": ensure_csrf(request),
        "user": user,
        "imprint": {
            "name": settings.imprint_name,
            "address": settings.imprint_address,
            "email": settings.imprint_email,
        },
        **context,
    }
    return templates.TemplateResponse(request, name, ctx)
