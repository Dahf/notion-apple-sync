from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .auth import ensure_csrf
from .db import SessionLocal
from .flash import pop_flash
from .i18n import SUPPORTED, get_locale, make_translator
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

    locale = get_locale(request)
    _ = make_translator(locale)

    path_no_locale = getattr(request.state, "path_no_locale", None) or request.url.path
    if locale == "en":
        canonical_url = f"{settings.base_url}/en{path_no_locale}"
    else:
        canonical_url = f"{settings.base_url}{path_no_locale}"
    locale_urls = {
        "de": f"{settings.base_url}{path_no_locale}",
        "en": f"{settings.base_url}/en{path_no_locale}",
        "x-default": f"{settings.base_url}{path_no_locale}",
    }

    ctx = {
        "base_url": settings.base_url,
        "csrf_token": ensure_csrf(request),
        "user": user,
        "flash_messages": pop_flash(request, locale),
        "imprint": {
            "name": settings.imprint_name,
            "address": settings.imprint_address,
            "email": settings.imprint_email,
        },
        "locale": locale,
        "supported_locales": SUPPORTED,
        "canonical_url": canonical_url,
        "locale_urls": locale_urls,
        "path_no_locale": path_no_locale,
        "_": _,
        "t": _,
        **context,
    }
    return templates.TemplateResponse(request, name, ctx)
