"""Unified application entry point for LifeOps AI + Self-X Evolution Engine.

Mounts the FastAPI API (with WebSocket real-time events) into the FastHTML
web application so a single ASGI server exposes both the Web UI and the API.

Run with:
    python -m lifeops.main            # development, auto-reload
    uvicorn lifeops.main:app          # production-style
"""
import os

from fasthtml.common import serve
from starlette.staticfiles import StaticFiles

from lifeops.api.router import app as api_app
from lifeops.storage.database import get_engine, init_db
from lifeops.web.app_ui import app

# Mount the API under the same ASGI app (API routes take precedence over UI routes).
app.mount("/", api_app)


def startup():
    engine = get_engine()
    init_db(engine)
    return engine


STATIC_DIR = os.path.join(os.path.dirname(__file__), "web", "static")


def create_app():
    """Create and configure the combined ASGI application."""
    if not any(getattr(m, "name", None) == "static" for m in app.routes):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    startup()
    return app


if __name__ == "__main__":
    create_app()
    serve(app_name="lifeops.main", app="app", reload=True)
