from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..auth import consume_magic_link, create_magic_link, login_session, logout_session
from ..cache import TTLCache
from ..crypto import decrypt
from ..db import get_session
from ..flash import flash
from ..i18n import (
    SUPPORTED,
    build_locale_url,
    get_locale,
    lredirect,
    strip_locale_prefix,
    translate,
)
from ..ics import build_ics
from ..mailer import send_email
from ..models import Calendar
from ..notion import fetch_events
from ..settings import settings
from ..templating import render, templates

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
_ics_cache = TTLCache(ttl_seconds=settings.cache_ttl)


def _notify_admin(request: Request, *, subject: str, title: str, email: str) -> None:
    if not settings.admin_email:
        return
    if email.lower() == settings.admin_email.lower():
        return  # kein Self-Spam

    from datetime import datetime, timezone
    import html as _html

    ip = request.client.host if request.client else "?"
    ua = request.headers.get("user-agent", "?")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    body = (
        f'<div style="font-family:-apple-system,Segoe UI,sans-serif; color:#0f172a;">'
        f'<div style="font-weight:600; font-size:15px; margin-bottom:8px;">{_html.escape(title)}</div>'
        f'<table style="border-collapse:collapse; font-size:13px;">'
        f'<tr><td style="padding:2px 8px 2px 0; color:#64748b;">Email</td>'
        f'<td><code>{_html.escape(email)}</code></td></tr>'
        f'<tr><td style="padding:2px 8px 2px 0; color:#64748b;">Zeit</td><td>{ts}</td></tr>'
        f'<tr><td style="padding:2px 8px 2px 0; color:#64748b;">IP</td><td><code>{_html.escape(ip)}</code></td></tr>'
        f'<tr><td style="padding:2px 8px 2px 0; color:#64748b;">Browser</td><td style="font-size:11px;">{_html.escape(ua)}</td></tr>'
        f'</table></div>'
    )
    text = f"{title}\nEmail: {email}\nZeit: {ts}\nIP: {ip}\nBrowser: {ua}"
    try:
        send_email(settings.admin_email, subject, body, text=text)
    except Exception:
        pass


@router.get("/")
def landing(request: Request):
    return render(request, "landing.html")


@router.get("/login")
def login_form(request: Request):
    return render(request, "login.html")


@router.post("/lang/{code}")
def set_language(code: str, request: Request):
    if code not in SUPPORTED:
        return RedirectResponse("/", status_code=303)

    referer = request.headers.get("referer") or "/"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(referer)
        referer_path = parsed.path or "/"
    except Exception:
        referer_path = "/"

    _, path_no_locale = strip_locale_prefix(referer_path)
    target = build_locale_url(path_no_locale, code)
    return RedirectResponse(target, status_code=303)


@router.post("/auth/request")
@limiter.limit("10/10 minutes")
def auth_request(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_session),
):
    email = email.strip().lower()
    locale = get_locale(request)
    if "@" in email and "." in email.split("@")[-1]:
        raw = create_magic_link(db, email)
        link = f"{settings.base_url}/auth/verify?token={raw}"
        html = templates.get_template("email/magic_link.html").render(
            link=link,
            base_url=settings.base_url,
            _=lambda k, **p: translate(k, locale, **p),
            locale=locale,
        )
        text = translate("email.text", locale, link=link)
        subject = translate("email.subject", locale)
        try:
            send_email(email, subject, html, text=text)
        except Exception:
            pass  # don't leak errors to UI

        _notify_admin(
            request,
            subject=f"[notion-calendar] 🔗 Magic-Link angefordert: {email}",
            title="🔗 Magic-Link angefordert",
            email=email,
        )
    return render(request, "login_sent.html", email=email)


@router.get("/auth/verify")
def auth_verify(token: str, request: Request, db: Session = Depends(get_session)):
    user = consume_magic_link(db, token)
    if user is None:
        locale = get_locale(request)
        return render(
            request, "login.html", error=translate("login.error_invalid", locale)
        )
    login_session(request, user)
    _notify_admin(
        request,
        subject=f"[notion-calendar] ✅ Login: {user.email}",
        title="✅ Erfolgreicher Login",
        email=user.email,
    )
    flash(request, "flash.welcome", kind="success", email=user.email)
    return RedirectResponse(lredirect(request, "/dashboard"), status_code=303)


@router.post("/auth/logout")
def auth_logout(request: Request):
    logout_session(request)
    flash(request, "flash.logged_out", kind="info")
    return RedirectResponse(lredirect(request, "/"), status_code=303)


@router.get("/privacy")
def privacy(request: Request):
    return render(request, "privacy.html")


@router.get("/imprint")
def imprint(request: Request):
    return render(request, "imprint.html")


@router.api_route("/cal/{token}.ics", methods=["GET", "HEAD"])
@limiter.limit("60/minute")
def ics_feed(token: str, request: Request, db: Session = Depends(get_session)):
    calendar = db.query(Calendar).filter(Calendar.subscription_token == token).one_or_none()
    if calendar is None:
        raise HTTPException(status_code=404, detail="Unknown calendar")

    cached = _ics_cache.get(token)
    if cached is None:
        access_token = decrypt(calendar.connection.notion_access_token_enc)
        events = fetch_events(
            access_token,
            calendar.database_id,
            calendar.date_property,
            calendar.description_property,
        )
        cached = build_ics(calendar, events)
        _ics_cache.set(token, cached)

    return Response(
        content=cached,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{calendar.name}.ics"',
            "Cache-Control": "public, max-age=600",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /dashboard\n"
        "Disallow: /auth/\n"
        "Disallow: /oauth/\n"
        "Disallow: /cal/\n"
        "Disallow: /lang/\n"
        "Disallow: /webhooks/\n"
        f"\nSitemap: {settings.base_url}/sitemap.xml\n"
    )


_SITEMAP_PATHS: tuple[tuple[str, str], ...] = (
    ("/", "weekly"),
    ("/login", "monthly"),
    ("/imprint", "yearly"),
    ("/privacy", "yearly"),
)


@router.get("/sitemap.xml")
def sitemap_xml():
    items = []
    for path, changefreq in _SITEMAP_PATHS:
        en = f"{settings.base_url}{build_locale_url(path, 'en')}"
        de = f"{settings.base_url}{build_locale_url(path, 'de')}"
        default = f"{settings.base_url}{build_locale_url(path, 'en')}"
        for canonical in (en, de):
            items.append(
                f"  <url>\n"
                f"    <loc>{canonical}</loc>\n"
                f"    <changefreq>{changefreq}</changefreq>\n"
                f'    <xhtml:link rel="alternate" hreflang="en" href="{en}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="de" href="{de}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{default}"/>\n'
                f"  </url>\n"
            )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "".join(items)
        + "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@router.get("/google5c627a1c647d3cc7.html", response_class=PlainTextResponse)
def google_site_verification():
    return "google-site-verification: google5c627a1c647d3cc7.html"


@router.api_route("/en", methods=["GET", "HEAD"])
@router.api_route("/en/{rest:path}", methods=["GET", "HEAD"])
def legacy_en_redirect(rest: str = ""):
    """Old URLs from before EN became the default — redirect to canonical root."""
    target = "/" + rest if rest else "/"
    return RedirectResponse(target, status_code=301)
