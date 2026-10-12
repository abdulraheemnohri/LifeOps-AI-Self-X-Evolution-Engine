"""LifeOps AI + Self-X — unified entry point.

Single command:  python -m lifeops.main [--host H --port P]
Serves the FastHTML web UI (with static assets) and the REST API under
/api/v1 on the same ASGI app, plus the WebSocket event stream at /ws/events.
"""
import argparse


def create_app():
    from lifeops.web.app_ui import create_app as create_web_app
    app = create_web_app()

    # Mount the REST API router (/api/v1) and WebSocket events on the same app.
    from lifeops.api.router import app as api_app
    for route in list(api_app.routes):
        if getattr(route, "path", "").startswith("/api"):
            api_app.routes.remove(route)
            app.routes.append(route)
        elif getattr(route, "path", "") == "/ws/events":
            api_app.routes.remove(route)
            app.routes.append(route)

    # Initialize DB & start background scheduler/worker threads.
    from lifeops.storage.database import get_engine, get_session_factory, init_db
    engine = get_engine()
    init_db(engine)
    factory = get_session_factory(engine)
    from lifeops.scheduler.worker import WorkerQueue, Scheduler
    worker = WorkerQueue(factory)
    worker.recover_pending()
    worker.start()
    scheduler = Scheduler(factory, worker)
    scheduler.start()
    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start LifeOps AI + Self-X server")
    parser.add_argument("--host", default=None, help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default: 8000)")
    args = parser.parse_args(argv)

    host = args.host or "127.0.0.1"
    port = args.port or 8000
    try:
        with _DB_probe() as db:
            from lifeops.services.settings_service import SettingsService
            binding = SettingsService(db).get_section("security.network_binding") or {}
            if not args.host:
                host = binding.get("host", host)
            if not args.port:
                port = int(binding.get("port", port))
            if binding.get("expose_network") is False and host not in ("127.0.0.1", "localhost", "::1"):
                print(f"Refusing to bind {host}: network exposure disabled in settings "
                      f"(enable security.network_binding.expose_network first). Using 127.0.0.1.")
                host = "127.0.0.1"
    except Exception:
        pass

    from lifeops.web.app_ui import app
    print(f"LifeOps AI + Self-X listening on http://{host}:{port}")
    from fasthtml.common import serve
    serve(app, host=host, port=port)


class _DB_probe:
    def __enter__(self):
        from lifeops.storage.database import get_engine, get_session_factory, init_db
        engine = get_engine()
        init_db(engine)
        self.db = get_session_factory(engine)()
        return self.db

    def __exit__(self, *a):
        self.db.close()


if __name__ == "__main__":
    main()
