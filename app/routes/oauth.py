import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import current_user
from ..crypto import encrypt
from ..db import get_session
from ..flash import flash
from ..models import Connection
from ..notion_oauth import authorize_url, exchange_code

router = APIRouter()


@router.get("/oauth/start")
def oauth_start(request: Request, db: Session = Depends(get_session)):
    user = current_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    return RedirectResponse(authorize_url(state), status_code=303)


@router.get("/oauth/callback")
def oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_session),
):
    user = current_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    expected = request.session.pop("oauth_state", None)
    if not expected or not secrets.compare_digest(expected, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    data = exchange_code(code)
    conn = Connection(
        user_id=user.id,
        notion_access_token_enc=encrypt(data["access_token"]),
        workspace_name=data.get("workspace_name") or "Workspace",
        workspace_id=data.get("workspace_id") or "",
        workspace_icon=data.get("workspace_icon"),
        bot_id=data.get("bot_id") or "",
    )
    db.add(conn)
    db.commit()
    flash(request, "flash.ws_connected", kind="success", name=conn.workspace_name)
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/oauth/disconnect/{connection_id}")
def oauth_disconnect(
    connection_id: int,
    request: Request,
    db: Session = Depends(get_session),
):
    user = current_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    conn = db.query(Connection).filter(Connection.id == connection_id).one_or_none()
    if conn is None or conn.user_id != user.id:
        raise HTTPException(status_code=404)
    ws_name = conn.workspace_name
    db.delete(conn)
    db.commit()
    flash(request, "flash.ws_disconnected", kind="info", name=ws_name)
    return RedirectResponse("/dashboard", status_code=303)
