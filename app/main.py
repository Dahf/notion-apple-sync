from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse

from .db import init_db
from .routes import dashboard, oauth, public, webhooks
from .settings import settings


def create_app() -> FastAPI:
    init_db()

    app = FastAPI(title="notion-apple-sync")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        https_only=settings.base_url.startswith("https://"),
        same_site="lax",
        max_age=60 * 60 * 24 * 30,
    )
    app.add_middleware(SlowAPIMiddleware)
    app.state.limiter = public.limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return PlainTextResponse("Rate limit exceeded. Try again later.", status_code=429)

    app.include_router(public.router)
    app.include_router(oauth.router)
    app.include_router(dashboard.router)
    app.include_router(webhooks.router)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
