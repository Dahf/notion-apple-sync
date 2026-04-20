import base64
from urllib.parse import urlencode

import httpx

from .settings import settings

AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
TOKEN_URL = "https://api.notion.com/v1/oauth/token"


def authorize_url(state: str) -> str:
    params = {
        "client_id": settings.notion_oauth_client_id,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": settings.oauth_redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    auth = base64.b64encode(
        f"{settings.notion_oauth_client_id}:{settings.notion_oauth_client_secret}".encode()
    ).decode()
    resp = httpx.post(
        TOKEN_URL,
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.oauth_redirect_uri,
        },
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()
