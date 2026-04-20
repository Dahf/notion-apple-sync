from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from .config import CalendarConfig
from .notion import NotionEvent


def build_uid(page_id: str, calendar_token: str) -> str:
    return f"{page_id}@notion-sync.{calendar_token[:8]}"


def _parse_date(iso: str) -> date:
    return date.fromisoformat(iso)


def _parse_datetime(iso: str, tz_override: str | None) -> datetime:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if tz_override:
        try:
            dt = dt.astimezone(ZoneInfo(tz_override))
        except Exception:
            dt = dt.astimezone(timezone.utc)
    return dt


def _add_event(cal: Calendar, ev: NotionEvent, calendar_token: str) -> None:
    vevent = Event()
    vevent.add("uid", build_uid(ev.page_id, calendar_token))
    vevent.add("summary", ev.title)
    if ev.description:
        vevent.add("description", ev.description)

    if ev.all_day:
        start = _parse_date(ev.start)
        vevent.add("dtstart", start)
        if ev.end:
            end = _parse_date(ev.end) + timedelta(days=1)
        else:
            end = start + timedelta(days=1)
        vevent.add("dtend", end)
    else:
        start_dt = _parse_datetime(ev.start, ev.time_zone)
        vevent.add("dtstart", start_dt)
        if ev.end:
            end_dt = _parse_datetime(ev.end, ev.time_zone)
            vevent.add("dtend", end_dt)

    if ev.last_edited:
        try:
            stamp = datetime.fromisoformat(ev.last_edited.replace("Z", "+00:00"))
            vevent.add("last-modified", stamp)
            vevent.add("dtstamp", stamp)
        except ValueError:
            pass

    cal.add_component(vevent)


def build_ics(cfg: CalendarConfig, events: list[NotionEvent]) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//notion-apple-sync//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", cfg.name)
    cal.add("x-wr-timezone", "UTC")
    cal.add("x-published-ttl", "PT1H")

    for ev in events:
        _add_event(cal, ev, cfg.token)

    return cal.to_ical()
