from dataclasses import dataclass
from datetime import date, datetime

from icalendar import Calendar as ICal

from app.ics import build_ics, build_uid
from app.notion import NotionEvent, parse_page


@dataclass
class CalStub:
    token: str
    name: str


def make_cfg() -> CalStub:
    return CalStub(token="a7f3k9c2e1b8d4f6a7f3k9c2e1b8d4f6", name="Uni")


def parse_ics(ics_bytes: bytes) -> list:
    cal = ICal.from_ical(ics_bytes)
    return [c for c in cal.walk("VEVENT")]


def test_uid_stable():
    u1 = build_uid("page-abc", "token12345678")
    u2 = build_uid("page-abc", "token12345678")
    assert u1 == u2
    assert u1 == "page-abc@notion-sync.token123"


def test_uid_separates_calendars():
    assert build_uid("page-abc", "cal1tokenXXXX") != build_uid("page-abc", "cal2tokenYYYY")


def test_all_day_event_exclusive_end():
    ev = NotionEvent(
        page_id="p1", title="All Day", start="2026-04-20", end=None, time_zone=None,
        all_day=True, description=None, last_edited="2026-04-01T10:00:00.000Z",
    )
    v = parse_ics(build_ics(make_cfg(), [ev]))[0]
    assert v["dtstart"].dt == date(2026, 4, 20)
    assert v["dtend"].dt == date(2026, 4, 21)


def test_all_day_range_exclusive_end():
    ev = NotionEvent(
        page_id="p1", title="Range", start="2026-04-20", end="2026-04-22", time_zone=None,
        all_day=True, description=None, last_edited="2026-04-01T10:00:00.000Z",
    )
    v = parse_ics(build_ics(make_cfg(), [ev]))[0]
    assert v["dtstart"].dt == date(2026, 4, 20)
    assert v["dtend"].dt == date(2026, 4, 23)


def test_datetime_utc():
    ev = NotionEvent(
        page_id="p1", title="Meeting", start="2026-04-20T14:00:00.000Z",
        end="2026-04-20T15:00:00.000Z", time_zone=None, all_day=False,
        description=None, last_edited="2026-04-01T10:00:00.000Z",
    )
    v = parse_ics(build_ics(make_cfg(), [ev]))[0]
    dt = v["dtstart"].dt
    assert isinstance(dt, datetime)
    assert dt.utcoffset().total_seconds() == 0
    assert dt.hour == 14


def test_datetime_with_timezone():
    ev = NotionEvent(
        page_id="p1", title="Berlin", start="2026-04-20T14:00:00.000+02:00",
        end="2026-04-20T15:00:00.000+02:00", time_zone="Europe/Berlin",
        all_day=False, description=None, last_edited="2026-04-01T10:00:00.000Z",
    )
    v = parse_ics(build_ics(make_cfg(), [ev]))[0]
    dt = v["dtstart"].dt
    assert dt.hour == 14
    assert "Berlin" in str(dt.tzinfo)


def test_parse_page_all_day():
    page = {
        "id": "page-xyz",
        "last_edited_time": "2026-04-01T10:00:00.000Z",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Hello"}]},
            "Datum": {"type": "date", "date": {"start": "2026-04-20", "end": None, "time_zone": None}},
            "Notizen": {"type": "rich_text", "rich_text": [{"plain_text": "note body"}]},
        },
    }
    ev = parse_page(page, "Datum", "Notizen")
    assert ev is not None
    assert ev.title == "Hello"
    assert ev.all_day is True
    assert ev.description == "note body"


def test_parse_page_skips_without_date():
    page = {
        "id": "page-xyz",
        "last_edited_time": "2026-04-01T10:00:00.000Z",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Hello"}]},
            "Datum": {"type": "date", "date": None},
        },
    }
    assert parse_page(page, "Datum", None) is None


def test_ics_has_calendar_headers():
    text = build_ics(make_cfg(), []).decode("utf-8")
    assert "PRODID:-//notion-apple-sync//DE" in text
    assert "X-WR-CALNAME:Uni" in text
    assert "VERSION:2.0" in text
