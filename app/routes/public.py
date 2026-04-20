from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..auth import consume_magic_link, create_magic_link, login_session, logout_session
from ..cache import TTLCache
from ..crypto import decrypt
from ..db import get_session
from ..flash import flash
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


@router.post("/auth/request")
@limiter.limit("10/10 minutes")
def auth_request(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_session),
):
    email = email.strip().lower()
    if "@" in email and "." in email.split("@")[-1]:
        raw = create_magic_link(db, email)
        link = f"{settings.base_url}/auth/verify?token={raw}"
        html = templates.get_template("email/magic_link.html").render(
            link=link, base_url=settings.base_url
        )
        text = (
            f"Dein Login-Link für Notion → Calendar:\n\n"
            f"{link}\n\n"
            f"Der Link ist 15 Minuten gültig und kann nur einmal verwendet werden.\n"
            f"Wenn du das nicht warst, ignoriere diese Mail."
        )
        try:
            send_email(email, "Dein Login-Link", html, text=text)
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
        return render(request, "login.html", error="Link ungültig oder abgelaufen.")
    login_session(request, user)
    _notify_admin(
        request,
        subject=f"[notion-calendar] ✅ Login: {user.email}",
        title="✅ Erfolgreicher Login",
        email=user.email,
    )
    flash(request, f"Willkommen, {user.email}.", kind="success")
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/auth/logout")
def auth_logout(request: Request):
    logout_session(request)
    flash(request, "Ausgeloggt. Bis bald.", kind="info")
    return RedirectResponse("/", status_code=303)


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
        },
    )
