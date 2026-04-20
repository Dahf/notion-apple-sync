from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .auth import ensure_csrf
from .db import SessionLocal
from .flash import pop_flash
from .i18n import (
    DEFAULT,
    SUPPORTED,
    build_locale_url,
    detect_preferred_language,
    get_locale,
    get_path_no_locale,
    make_translator,
)
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

    def lurl(path: str) -> str:
        return build_locale_url(path, locale)

    path_no_locale = get_path_no_locale(request)
    canonical_url = f"{settings.base_url}{build_locale_url(path_no_locale, locale)}"
    locale_urls = {
        "en": f"{settings.base_url}{build_locale_url(path_no_locale, 'en')}",
        "de": f"{settings.base_url}{build_locale_url(path_no_locale, 'de')}",
        "x-default": f"{settings.base_url}{build_locale_url(path_no_locale, DEFAULT)}",
    }

    # Soft language-suggestion banner: shown once per user (cookie-dismissable)
    # when the browser's preferred language differs from the current locale.
    preferred = detect_preferred_language(request)
    banner_dismissed = request.cookies.get("lang_banner") == "1"
    suggest_locale = None
    if not banner_dismissed and preferred in SUPPORTED and preferred != locale:
        suggest_locale = preferred
    suggest_url = build_locale_url(path_no_locale, suggest_locale) if suggest_locale else None

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
        "suggest_locale": suggest_locale,
        "suggest_url": suggest_url,
        "_": _,
        "t": _,
        "lurl": lurl,
        **context,
    }
    return templates.TemplateResponse(request, name, ctx)
