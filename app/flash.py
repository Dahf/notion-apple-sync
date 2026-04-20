from fastapi import Request


def flash(request: Request, message: str, kind: str = "info") -> None:
    """Add a flash message (shown as toast on next render)."""
    if not hasattr(request, "session"):
        return
    msgs = request.session.get("flash", [])
    msgs.append({"kind": kind, "message": message})
    request.session["flash"] = msgs


def pop_flash(request: Request) -> list[dict]:
    if not hasattr(request, "session"):
        return []
    return request.session.pop("flash", []) or []
