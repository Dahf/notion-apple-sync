from dataclasses import dataclass
from typing import Any

from notion_client import Client


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


@dataclass
class NotionDatabaseInfo:
    id: str
    title: str
    date_properties: list[str]
    text_properties: list[str]


def _extract_plain_text(rich_text: list[dict[str, Any]] | None) -> str:
    if not rich_text:
        return ""
    return "".join(block.get("plain_text", "") for block in rich_text)


def _extract_title_from_properties(properties: dict[str, Any]) -> str:
    for prop in properties.values():
        if prop.get("type") == "title":
            return _extract_plain_text(prop.get("title", []))
    return ""


def _is_all_day(iso: str) -> bool:
    return "T" not in iso


def parse_page(
    page: dict[str, Any],
    date_property: str,
    description_property: str | None,
) -> NotionEvent | None:
    props = page.get("properties", {})
    date_prop = props.get(date_property)
    if not date_prop or date_prop.get("type") != "date":
        return None
    date_value = date_prop.get("date")
    if not date_value or not date_value.get("start"):
        return None

    description: str | None = None
    if description_property:
        desc_prop = props.get(description_property)
        if desc_prop:
            ptype = desc_prop.get("type")
            if ptype == "rich_text":
                description = _extract_plain_text(desc_prop.get("rich_text", [])) or None
            elif ptype == "title":
                description = _extract_plain_text(desc_prop.get("title", [])) or None
            elif ptype == "select":
                val = desc_prop.get("select")
                description = val.get("name") if val else None
            elif ptype == "multi_select":
                vals = desc_prop.get("multi_select") or []
                description = ", ".join(v.get("name", "") for v in vals) or None

    start = date_value["start"]
    end = date_value.get("end")
    return NotionEvent(
        page_id=page["id"],
        title=_extract_title_from_properties(props) or "(kein Titel)",
        start=start,
        end=end,
        time_zone=date_value.get("time_zone"),
        all_day=_is_all_day(start) and (end is None or _is_all_day(end)),
        description=description,
        last_edited=page.get("last_edited_time", ""),
    )


def fetch_events(
    access_token: str,
    database_id: str,
    date_property: str,
    description_property: str | None,
) -> list[NotionEvent]:
    client = Client(auth=access_token)
    events: list[NotionEvent] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {"database_id": database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.databases.query(**kwargs)
        for page in resp.get("results", []):
            event = parse_page(page, date_property, description_property)
            if event is not None:
                events.append(event)
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return events


def list_databases(access_token: str) -> list[NotionDatabaseInfo]:
    client = Client(auth=access_token)
    results: list[NotionDatabaseInfo] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "filter": {"property": "object", "value": "database"},
            "page_size": 100,
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.search(**kwargs)
        for db in resp.get("results", []):
            if db.get("object") != "database":
                continue
            results.append(_db_info(db))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return results


def _db_info(db: dict[str, Any]) -> NotionDatabaseInfo:
    title = _extract_plain_text(db.get("title", [])) or "(Untitled)"
    date_props: list[str] = []
    text_props: list[str] = []
    for name, prop in (db.get("properties") or {}).items():
        ptype = prop.get("type")
        if ptype == "date":
            date_props.append(name)
        elif ptype in ("rich_text", "select", "multi_select", "title"):
            text_props.append(name)
    return NotionDatabaseInfo(
        id=db["id"], title=title, date_properties=date_props, text_properties=text_props
    )


def get_database_properties(access_token: str, database_id: str) -> NotionDatabaseInfo:
    client = Client(auth=access_token)
    db = client.databases.retrieve(database_id=database_id)
    return _db_info(db)
