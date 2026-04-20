import logging

import httpx

from .settings import settings

log = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str, text: str | None = None) -> None:
    if not settings.resend_api_key:
        log.warning("RESEND_API_KEY not set — email not sent. Link: %s", _extract_link(html))
        return

    payload: dict = {
        "from": settings.mail_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    resp = httpx.post(
        RESEND_URL,
        json=payload,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        timeout=10.0,
    )
    if resp.status_code >= 400:
        log.error("Resend error %s: %s", resp.status_code, resp.text)
        raise RuntimeError(f"Email send failed: {resp.status_code}")


def _extract_link(html: str) -> str:
    import re
    match = re.search(r'href="([^"]+)"', html)
    return match.group(1) if match else "<no link>"
