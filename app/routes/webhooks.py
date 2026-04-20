import base64
import hashlib
import hmac
import html
import json
import logging
import time
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Request

from ..mailer import send_email
from ..settings import settings

router = APIRouter()
log = logging.getLogger(__name__)

MAX_SKEW_SECONDS = 60 * 5

HANDLED_EVENTS = {"email.received", "email.sent", "email.failed"}


def _verify_svix_signature(body: bytes, headers) -> bool:
    if not settings.resend_webhook_secret:
        return True

    svix_id = headers.get("svix-id") or headers.get("webhook-id")
    svix_timestamp = headers.get("svix-timestamp") or headers.get("webhook-timestamp")
    svix_signature = headers.get("svix-signature") or headers.get("webhook-signature")
    if not (svix_id and svix_timestamp and svix_signature):
        return False

    try:
        ts = int(svix_timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > MAX_SKEW_SECONDS:
        return False

    secret = settings.resend_webhook_secret
    if secret.startswith("whsec_"):
        secret = secret[len("whsec_"):]
    try:
        secret_bytes = base64.b64decode(secret)
    except Exception:
        return False

    signed = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()

    for part in svix_signature.split(" "):
        if "," in part:
            _, sig = part.split(",", 1)
            if hmac.compare_digest(sig, expected):
                return True
    return False


def _sender_of(data: dict[str, Any]) -> str:
    src = data.get("from")
    if isinstance(src, list) and src:
        src = src[0]
    if isinstance(src, dict):
        return src.get("email") or src.get("address") or ""
    return src or ""


def _recipients_of(data: dict[str, Any]) -> str:
    raw = data.get("to") or []
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for t in raw:
        if isinstance(t, dict):
            out.append(t.get("email") or t.get("address") or "")
        else:
            out.append(str(t))
    return ", ".join(x for x in out if x)


def _pre(text: str) -> str:
    return (
        f'<pre style="white-space:pre-wrap; font-family:ui-monospace,Menlo,monospace; '
        f'font-size:13px; color:#334155;">{html.escape(text[:10000])}</pre>'
    )


def _card(title: str, color: str, rows: list[tuple[str, str]], body: str | None = None) -> str:
    row_html = "".join(
        f'<tr><td style="padding:4px 8px 4px 0; color:#64748b; font-size:13px;">{html.escape(k)}</td>'
        f'<td style="padding:4px 0; color:#0f172a; font-size:13px;"><code>{html.escape(v)}</code></td></tr>'
        for k, v in rows
    )
    body_html = f"<hr style=\"border:0; border-top:1px solid #e2e8f0; margin:16px 0;\">{body}" if body else ""
    return (
        f'<div style="border-left:4px solid {color}; padding:12px 16px; background:#f8fafc;">'
        f'<div style="font-weight:600; font-size:15px; color:#0f172a; margin-bottom:8px;">{html.escape(title)}</div>'
        f'<table style="border-collapse:collapse;">{row_html}</table>'
        f'{body_html}</div>'
    )


def _handle_received(data: dict[str, Any]) -> tuple[str, str, str]:
    sender = _sender_of(data)
    to_str = _recipients_of(data)
    subject_in = data.get("subject") or "(kein Betreff)"
    text = data.get("text") or data.get("html") or ""
    body = _card(
        "📬 Neue Kontakt-Mail",
        "#0ea5e9",
        [("Von", sender), ("An", to_str), ("Betreff", subject_in)],
        _pre(text) if text else None,
    )
    text_fallback = f"Kontakt-Mail\nVon: {sender}\nAn: {to_str}\nBetreff: {subject_in}\n\n{text[:10000]}"
    return f"[notion-calendar] Kontakt von {sender}: {subject_in}", body, text_fallback


def _handle_sent(data: dict[str, Any]) -> tuple[str, str, str]:
    to_str = _recipients_of(data)
    subj = data.get("subject") or "(kein Betreff)"
    email_id = data.get("email_id") or data.get("id") or ""
    body = _card(
        "✅ Mail gesendet",
        "#10b981",
        [("An", to_str), ("Betreff", subj), ("Resend-ID", email_id)],
    )
    return f"[notion-calendar] ✅ sent → {to_str}", body, f"Sent to {to_str}\nSubject: {subj}\nID: {email_id}"


def _handle_failed(data: dict[str, Any]) -> tuple[str, str, str]:
    to_str = _recipients_of(data)
    subj = data.get("subject") or "(kein Betreff)"
    email_id = data.get("email_id") or data.get("id") or ""
    failure = data.get("failed") or {}
    reason = ""
    if isinstance(failure, dict):
        reason = failure.get("reason") or failure.get("message") or ""
    if not reason:
        reason = data.get("reason") or data.get("error") or "unbekannt"
    body = _card(
        "⚠️ Mail-Versand fehlgeschlagen",
        "#ef4444",
        [("An", to_str), ("Betreff", subj), ("Resend-ID", email_id), ("Grund", reason)],
    )
    return (
        f"[notion-calendar] ⚠️ FAILED → {to_str}",
        body,
        f"FAILED\nAn: {to_str}\nBetreff: {subj}\nGrund: {reason}\nID: {email_id}",
    )


HANDLERS: dict[str, Callable[[dict[str, Any]], tuple[str, str, str]]] = {
    "email.received": _handle_received,
    "email.sent": _handle_sent,
    "email.failed": _handle_failed,
}


@router.post("/webhooks/resend/inbound")
async def resend_webhook(request: Request):
    body = await request.body()
    if not _verify_svix_signature(body, request.headers):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type", "")
    if event_type not in HANDLED_EVENTS:
        return {"ok": True, "ignored": event_type}

    if not settings.admin_email:
        log.warning("%s received but ADMIN_EMAIL not configured", event_type)
        return {"ok": True, "skipped": "no_admin"}

    data = payload.get("data") or {}
    handler = HANDLERS[event_type]
    subject, html_body, text_body = handler(data)

    try:
        send_email(settings.admin_email, subject, html_body, text=text_body)
    except Exception as e:
        log.exception("Admin-forward failed: %s", e)
        raise HTTPException(status_code=500, detail="Forward failed")

    return {"ok": True, "forwarded": event_type}
