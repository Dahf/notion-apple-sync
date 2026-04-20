from dataclasses import dataclass
from typing import Any

from notion_client import Client

from .config import CalendarConfig


@dataclass
class NotionEvent:
    page_id: str
    title: str
    start: str
    end: str | None
    time_zone: str | None
    all_day: bool
    description: str | None
    last_edited: str


def _extract_plain_text(rich_text: list[dict[str, Any]] | None) -> str:
    if not rich_text:
        return ""
    return "".join(block.get("plain_text", "") for block in rich_text)


def _extract_title(properties: dict[str, Any]) -> str:
    for prop in properties.values():
        if prop.get("type") == "title":
            return _extract_plain_text(prop.get("title", []))
    return ""


def _is_all_day(iso: str) -> bool:
    return "T" not in iso


def parse_page(page: dict[str, Any], cfg: CalendarConfig) -> NotionEvent | None:
    props = page.get("properties", {})
    date_prop = props.get(cfg.properties.date)
    if not date_prop or date_prop.get("type") != "date":
        return None
    date_value = date_prop.get("date")
    if not date_value or not date_value.get("start"):
        return None

    description: str | None = None
    if cfg.properties.description:
        desc_prop = props.get(cfg.properties.description)
        if desc_prop:
            ptype = desc_prop.get("type")
            if ptype == "rich_text":
                description = _extract_plain_text(desc_prop.get("rich_text", [])) or None
            elif ptype == "title":
                description = _extract_plain_text(desc_prop.get("title", [])) or None

    start = date_value["start"]
    end = date_value.get("end")
    return NotionEvent(
        page_id=page["id"],
        title=_extract_title(props) or "(kein Titel)",
        start=start,
        end=end,
        time_zone=date_value.get("time_zone"),
        all_day=_is_all_day(start) and (end is None or _is_all_day(end)),
        description=description,
        last_edited=page.get("last_edited_time", ""),
    )


def fetch_events(client: Client, cfg: CalendarConfig) -> list[NotionEvent]:
    events: list[NotionEvent] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {"database_id": cfg.database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.databases.query(**kwargs)
        for page in resp.get("results", []):
            event = parse_page(page, cfg)
            if event is not None:
                events.append(event)
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return events
