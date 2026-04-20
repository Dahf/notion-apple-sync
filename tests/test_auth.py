from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import consume_magic_link, create_magic_link, hash_token
from app.db import Base
from app.models import MagicLink, User


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_create_magic_link_stores_hash_only():
    db = make_session()
    raw = create_magic_link(db, "foo@example.com")
    links = db.query(MagicLink).all()
    assert len(links) == 1
    assert links[0].token_hash == hash_token(raw)
    assert links[0].token_hash != raw
    assert links[0].email == "foo@example.com"


def test_consume_valid_token_creates_user():
    db = make_session()
    raw = create_magic_link(db, "new@example.com")
    user = consume_magic_link(db, raw)
    assert user is not None
    assert user.email == "new@example.com"
    assert db.query(User).count() == 1

    link = db.query(MagicLink).first()
    assert link.used_at is not None


def test_consume_twice_fails():
    db = make_session()
    raw = create_magic_link(db, "a@b.c")
    assert consume_magic_link(db, raw) is not None
    assert consume_magic_link(db, raw) is None


def test_consume_expired_fails():
    db = make_session()
    raw = create_magic_link(db, "a@b.c")
    link = db.query(MagicLink).one()
    link.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert consume_magic_link(db, raw) is None


def test_consume_unknown_token_fails():
    db = make_session()
    assert consume_magic_link(db, "garbage-token") is None


def test_consume_reuses_existing_user():
    db = make_session()
    existing = User(email="exists@example.com")
    db.add(existing)
    db.commit()

    raw = create_magic_link(db, "exists@example.com")
    user = consume_magic_link(db, raw)
    assert user.id == existing.id
    assert db.query(User).count() == 1
