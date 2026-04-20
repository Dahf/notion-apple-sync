import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from notion_client import Client

from .cache import TTLCache
from .config import AppConfig, load_config
from .ics import build_ics
from .notion import fetch_events

load_dotenv()

app = FastAPI(title="notion-apple-sync")

_config: AppConfig = load_config(os.getenv("CONFIG_PATH", "config.yaml"))
_notion = Client(auth=os.environ["NOTION_TOKEN"])
_cache = TTLCache(ttl_seconds=int(os.getenv("CACHE_TTL", "600")))


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/cal/{token}.ics")
def calendar_feed(token: str) -> Response:
    cfg = _config.by_token(token)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Unknown calendar")

    cached = _cache.get(token)
    if cached is None:
        events = fetch_events(_notion, cfg)
        cached = build_ics(cfg, events)
        _cache.set(token, cached)

    return Response(
        content=cached,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{cfg.name}.ics"',
            "Cache-Control": "public, max-age=600",
        },
    )
