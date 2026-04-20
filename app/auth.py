import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy.orm import Session

from .models import MagicLink, User

MAGIC_LINK_TTL_MINUTES = 15


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_magic_link(db: Session, email: str) -> str:
    raw = secrets.token_urlsafe(32)
    link = MagicLink(
        email=email.strip().lower(),
        token_hash=hash_token(raw),
        expires_at=_now() + timedelta(minutes=MAGIC_LINK_TTL_MINUTES),
    )
    db.add(link)
    db.commit()
    return raw


def consume_magic_link(db: Session, raw_token: str) -> User | None:
    th = hash_token(raw_token)
    link = db.query(MagicLink).filter(MagicLink.token_hash == th).one_or_none()
    if link is None or link.used_at is not None:
        return None
    expires_at = link.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < _now():
        return None

    link.used_at = _now()

    user = db.query(User).filter(User.email == link.email).one_or_none()
    if user is None:
        user = User(email=link.email)
        db.add(user)
        db.flush()
    user.last_login_at = _now()

    db.commit()
    return user


def login_session(request: Request, user: User) -> None:
    request.session["user_id"] = user.id


def logout_session(request: Request) -> None:
    request.session.pop("user_id", None)


def current_user(request: Request, db: Session) -> User | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    return db.query(User).filter(User.id == uid).one_or_none()


def ensure_csrf(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def verify_csrf(request: Request, submitted: str | None) -> bool:
    expected = request.session.get("csrf")
    if not expected or not submitted:
        return False
    return secrets.compare_digest(expected, submitted)
