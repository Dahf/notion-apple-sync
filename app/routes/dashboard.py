import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import current_user, verify_csrf
from ..crypto import decrypt
from ..db import get_session
from ..models import Calendar, Connection
from ..notion import get_database_properties, list_databases
from ..settings import settings
from ..templating import render

router = APIRouter()


def _require_user(request: Request, db: Session):
    user = current_user(request, db)
    if user is None:
        return None
    return user


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_session)):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)

    connections = db.query(Connection).filter(Connection.user_id == user.id).all()
    calendars_by_conn = {
        c.id: db.query(Calendar).filter(Calendar.connection_id == c.id).all()
        for c in connections
    }
    return render(
        request,
        "dashboard.html",
        user=user,
        connections=connections,
        calendars_by_conn=calendars_by_conn,
    )


@router.get("/dashboard/connections/{connection_id}/databases")
def htmx_list_databases(
    connection_id: int, request: Request, db: Session = Depends(get_session)
):
    user = _require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401)
    conn = db.query(Connection).filter(Connection.id == connection_id).one_or_none()
    if conn is None or conn.user_id != user.id:
        raise HTTPException(status_code=404)
    access = decrypt(conn.notion_access_token_enc)
    dbs = list_databases(access)
    return render(request, "partials/db_picker.html", databases=dbs, connection=conn)


@router.get("/dashboard/connections/{connection_id}/databases/{database_id}/properties")
def htmx_db_properties(
    connection_id: int,
    database_id: str,
    request: Request,
    db: Session = Depends(get_session),
):
    user = _require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401)
    conn = db.query(Connection).filter(Connection.id == connection_id).one_or_none()
    if conn is None or conn.user_id != user.id:
        raise HTTPException(status_code=404)
    access = decrypt(conn.notion_access_token_enc)
    info = get_database_properties(access, database_id)
    return render(
        request,
        "partials/property_picker.html",
        info=info,
        connection=conn,
    )


@router.post("/dashboard/calendars")
def create_calendar(
    request: Request,
    connection_id: int = Form(...),
    database_id: str = Form(...),
    name: str = Form(...),
    date_property: str = Form(...),
    description_property: str | None = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_session),
):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not verify_csrf(request, csrf_token):
        raise HTTPException(status_code=400, detail="CSRF check failed")

    conn = db.query(Connection).filter(Connection.id == connection_id).one_or_none()
    if conn is None or conn.user_id != user.id:
        raise HTTPException(status_code=404)

    cal = Calendar(
        connection_id=conn.id,
        subscription_token=secrets.token_urlsafe(32),
        name=name.strip() or "Kalender",
        database_id=database_id,
        date_property=date_property,
        description_property=(description_property or None) or None,
    )
    db.add(cal)
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/dashboard/calendars/{calendar_id}/delete")
def delete_calendar(
    calendar_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_session),
):
    user = _require_user(request, db)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if not verify_csrf(request, csrf_token):
        raise HTTPException(status_code=400)

    cal = db.query(Calendar).filter(Calendar.id == calendar_id).one_or_none()
    if cal is None or cal.connection.user_id != user.id:
        raise HTTPException(status_code=404)
    db.delete(cal)
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)
