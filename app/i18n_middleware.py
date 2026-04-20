from starlette.types import ASGIApp, Receive, Scope, Send

from .i18n import DEFAULT, SUPPORTED


def _split_locale(path: str) -> tuple[str, str]:
    """Return (locale, path_without_prefix). Defaults to DEFAULT locale if no prefix."""
    for code in SUPPORTED:
        if code == DEFAULT:
            continue
        prefix = f"/{code}"
        if path == prefix:
            return code, "/"
        if path.startswith(f"{prefix}/"):
            return code, path[len(prefix):]
    return DEFAULT, path


class LocaleMiddleware:
    """ASGI middleware: strip `/en` prefix from request path, expose locale in scope state."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        raw_path = scope.get("path", "/")
        locale, path_no_locale = _split_locale(raw_path)

        scope = dict(scope)
        scope["path"] = path_no_locale
        raw_path_bytes = scope.get("raw_path")
        if isinstance(raw_path_bytes, bytes):
            # Keep raw_path in sync so starlette's routing uses the rewritten path.
            try:
                query_sep = raw_path_bytes.find(b"?")
                if query_sep != -1:
                    scope["raw_path"] = path_no_locale.encode() + raw_path_bytes[query_sep:]
                else:
                    scope["raw_path"] = path_no_locale.encode()
            except Exception:
                scope["raw_path"] = path_no_locale.encode()

        # Use dedicated scope keys instead of scope["state"] to avoid conflicts with
        # SlowAPI (dict-based) and Starlette's Request.state (attribute-based).
        scope["locale"] = locale
        scope["path_no_locale"] = path_no_locale
        scope["original_path"] = raw_path

        await self.app(scope, receive, send)
