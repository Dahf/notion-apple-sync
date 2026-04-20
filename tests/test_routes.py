import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crypto import encrypt
from app.db import Base, get_session
from app.main import create_app
from app.models import Calendar, Connection, User


@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_session():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    return client, TestSession


def test_landing_ok(client_with_db):
    client, _ = client_with_db
    r = client.get("/")
    assert r.status_code == 200
    assert "Notion" in r.text


def test_health(client_with_db):
    client, _ = client_with_db
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_dashboard_redirects_without_session(client_with_db):
    client, _ = client_with_db
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_ics_unknown_token_404(client_with_db):
    client, _ = client_with_db
    r = client.get("/cal/nonexistent.ics")
    assert r.status_code == 404


def test_ics_returns_calendar_for_valid_token(client_with_db, monkeypatch):
    client, Session = client_with_db

    def fake_fetch_events(access_token, database_id, date_property, description_property):
        from app.notion import NotionEvent
        return [
            NotionEvent(
                page_id="p1", title="Test Event", start="2026-04-20",
                end=None, time_zone=None, all_day=True, description=None,
                last_edited="2026-04-01T10:00:00.000Z",
            )
        ]

    monkeypatch.setattr("app.routes.public.fetch_events", fake_fetch_events)

    db = Session()
    user = User(email="t@test.com")
    db.add(user)
    db.flush()
    conn = Connection(
        user_id=user.id,
        notion_access_token_enc=encrypt("secret_fake_token"),
        workspace_name="Test WS", workspace_id="ws1", bot_id="bot1",
    )
    db.add(conn)
    db.flush()
    cal = Calendar(
        connection_id=conn.id, subscription_token="test-sub-token",
        name="Uni", database_id="db1", date_property="Datum",
        description_property=None,
    )
    db.add(cal)
    db.commit()
    db.close()

    r = client.get("/cal/test-sub-token.ics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert b"BEGIN:VCALENDAR" in r.content
    assert b"Test Event" in r.content


def test_login_page_renders(client_with_db):
    client, _ = client_with_db
    r = client.get("/login")
    assert r.status_code == 200
    assert "Email" in r.text or "email" in r.text


def test_imprint_and_privacy(client_with_db):
    client, _ = client_with_db
    assert client.get("/imprint").status_code == 200
    assert client.get("/privacy").status_code == 200
