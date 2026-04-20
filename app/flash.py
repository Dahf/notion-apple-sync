from fastapi import Request

from .i18n import translate


def flash(request: Request, key: str, kind: str = "info", **params) -> None:
    """Queue a flash message (translated on next render)."""
    if not hasattr(request, "session"):
        return
    msgs = request.session.get("flash", [])
    msgs.append({"kind": kind, "key": key, "params": params})
    request.session["flash"] = msgs


def pop_flash(request: Request, locale: str) -> list[dict]:
    if not hasattr(request, "session"):
        return []
    raw = request.session.pop("flash", []) or []
    out: list[dict] = []
    for m in raw:
        if "key" in m:
            message = translate(m["key"], locale, **(m.get("params") or {}))
        else:
            message = m.get("message", "")
        out.append({"kind": m.get("kind", "info"), "message": message})
    return out
