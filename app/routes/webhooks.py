import base64
import hashlib
import hmac
import html
import logging
import time

from fastapi import APIRouter, HTTPException, Request

from ..mailer import send_email
from ..settings import settings

router = APIRouter()
log = logging.getLogger(__name__)

MAX_SKEW_SECONDS = 60 * 5


def _verify_svix_signature(body: bytes, headers) -> bool:
    """Verify Resend (Svix-compatible) webhook signature."""
    if not settings.resend_webhook_secret:
        return True  # no secret configured → accept (useful for local testing)

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


def _extract_text(event_data: dict) -> tuple[str, str, str, str]:
    """Extract sender, subject, text/html body from Resend inbound payload."""
    sender = event_data.get("from") or ""
    if isinstance(sender, dict):
        sender = sender.get("email") or sender.get("address") or ""
    if isinstance(event_data.get("from"), list) and event_data["from"]:
        first = event_data["from"][0]
        if isinstance(first, dict):
            sender = first.get("email") or first.get("address") or str(first)
        else:
            sender = str(first)

    to_list = event_data.get("to") or []
    if isinstance(to_list, list):
        to_str = ", ".join(
            (t.get("email") if isinstance(t, dict) else str(t)) for t in to_list
        )
    else:
        to_str = str(to_list)

    subject = event_data.get("subject") or "(kein Betreff)"
    text = event_data.get("text") or ""
    html_body = event_data.get("html") or ""
    if not text and html_body:
        text = html_body
    return sender, to_str, subject, text


@router.post("/webhooks/resend/inbound")
async def resend_inbound(request: Request):
    body = await request.body()
    if not _verify_svix_signature(body, request.headers):
        raise HTTPException(status_code=401, detail="Invalid signature")

    import json
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type", "")
    if event_type != "email.received":
        return {"ok": True, "skipped": event_type}

    if not settings.admin_email:
        log.warning("email.received but ADMIN_EMAIL not configured — dropping")
        return {"ok": True, "skipped": "no_admin"}

    data = payload.get("data") or {}
    sender, to_str, subject, text = _extract_text(data)

    body_html = (
        f"<p><strong>Neue Kontakt-Mail</strong> an <code>{html.escape(to_str)}</code></p>"
        f"<p><strong>Von:</strong> {html.escape(sender)}<br>"
        f"<strong>Betreff:</strong> {html.escape(subject)}</p>"
        f"<hr>"
        f"<pre style=\"white-space:pre-wrap; font-family:ui-monospace,Menlo,monospace; "
        f"font-size:13px; color:#334155;\">{html.escape(text[:10000])}</pre>"
    )
    try:
        send_email(
            settings.admin_email,
            f"[notion-calendar] Kontakt von {sender}: {subject}",
            body_html,
            text=f"Von: {sender}\nAn: {to_str}\nBetreff: {subject}\n\n{text[:10000]}",
        )
    except Exception as e:
        log.exception("Forward failed: %s", e)
        raise HTTPException(status_code=500, detail="Forward failed")

    return {"ok": True, "forwarded": True}
