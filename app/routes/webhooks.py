import base64
import hashlib
import hmac
import html
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..mailer import send_email
from ..settings import settings

router = APIRouter()
log = logging.getLogger(__name__)

MAX_SKEW_SECONDS = 60 * 5


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


@router.post("/webhooks/resend/inbound")
async def resend_webhook(request: Request):
    body = await request.body()
    if not _verify_svix_signature(body, request.headers):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if payload.get("type") != "email.received":
        return {"ok": True, "ignored": payload.get("type", "")}

    if not settings.admin_email:
        log.warning("email.received but ADMIN_EMAIL not configured")
        return {"ok": True, "skipped": "no_admin"}

    data = payload.get("data") or {}
    sender = _sender_of(data)
    to_str = _recipients_of(data)
    subject_in = data.get("subject") or "(kein Betreff)"
    text = data.get("text") or data.get("html") or ""

    admin_body = (
        f'<div style="font-family:-apple-system,Segoe UI,sans-serif; color:#0f172a;">'
        f'<div style="font-weight:600; font-size:15px; margin-bottom:8px;">📬 Neue Kontakt-Mail</div>'
        f'<table style="border-collapse:collapse; font-size:13px;">'
        f'<tr><td style="padding:2px 8px 2px 0; color:#64748b;">Von</td>'
        f'<td><code>{html.escape(sender)}</code></td></tr>'
        f'<tr><td style="padding:2px 8px 2px 0; color:#64748b;">An</td>'
        f'<td><code>{html.escape(to_str)}</code></td></tr>'
        f'<tr><td style="padding:2px 8px 2px 0; color:#64748b;">Betreff</td>'
        f'<td>{html.escape(subject_in)}</td></tr>'
        f'</table>'
        f'<hr style="border:0; border-top:1px solid #e2e8f0; margin:16px 0;">'
        f'<pre style="white-space:pre-wrap; font-family:ui-monospace,Menlo,monospace; '
        f'font-size:13px; color:#334155;">{html.escape(text[:10000])}</pre>'
        f'</div>'
    )
    text_fallback = f"Von: {sender}\nAn: {to_str}\nBetreff: {subject_in}\n\n{text[:10000]}"

    try:
        send_email(
            settings.admin_email,
            f"[notion-calendar] Kontakt von {sender}: {subject_in}",
            admin_body,
            text=text_fallback,
        )
    except Exception as e:
        log.exception("Admin-forward failed: %s", e)
        raise HTTPException(status_code=500, detail="Forward failed")

    return {"ok": True, "forwarded": True}
