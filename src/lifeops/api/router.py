"""LifeOps FastAPI application: assembles all /api/v1 routers, auth middleware,
WebSocket real-time events, and startup wiring for scheduler/workers."""
from typing import Any, Dict, List

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from lifeops.api.deps import (PUBLIC_API_PATHS, auth_enabled, current_user_from_request,
                              emergency_stop, get_db)
from lifeops.api.routers import admin, agents, auth, automation, lifeops_crud, selfx
from lifeops.storage.database import get_engine, get_session_factory, init_db


def create_api_app(start_background: bool = True) -> FastAPI:
    app = FastAPI(title="LifeOps AI + Self-X API", version="0.1.0")

    # ------------------------------------------------------------------
    # Auth middleware (enforced only when security.auth_enabled is true)
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/v1") and path not in PUBLIC_API_PATHS:
            db_generator = get_db()
            db = next(db_generator)
            try:
                from lifeops.storage.models import User
                users_exist = db.query(User.id).first() is not None
                # Never leave private API routes open merely because a settings
                # flag is missing or defaults to false.
                if not users_exist:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Initial administrator setup required"},
                    )
                user = current_user_from_request(request, db)
                if user is None:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication required"},
                    )
                request.state.user = user
            finally:
                try:
                    next(db_generator)
                except StopIteration:
                    pass
        return await call_next(request)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    for module in (auth, lifeops_crud, agents, selfx, automation, admin):
        app.include_router(module.router)

    # ------------------------------------------------------------------
    # WebSocket active connections
    # ------------------------------------------------------------------
    class ConnectionManager:
        def __init__(self):
            self.active_connections: List[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

        async def broadcast(self, message: Dict[str, Any]):
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    manager = ConnectionManager()
    app.state.ws_manager = manager

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await websocket.send_json({"type": "echo", "data": data})
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    # ------------------------------------------------------------------
    # Startup: DB, worker queue, scheduler; shutdown: stop threads
    # ------------------------------------------------------------------
    @app.on_event("startup")
    def _startup():
        engine = get_engine()
        init_db(engine)
        session_factory = get_session_factory(engine)
        from lifeops.tools.registry import ToolRegistry
        from lifeops.security.policy import PolicyEngine, ApprovalGate
        db = session_factory()
        try:
            app.state.tool_registry = ToolRegistry(PolicyEngine(), ApprovalGate(db))
        finally:
            db.close()
        if start_background:
            from lifeops.scheduler.worker import Scheduler, WorkerQueue
            from lifeops.services.settings_service import SettingsService
            db = session_factory()
            try:
                sched_cfg = SettingsService(db).get_section("scheduler")
            finally:
                db.close()
            queue = WorkerQueue(session_factory,
                                concurrency=int(sched_cfg.get("worker_concurrency", 2)),
                                queue_limit=int(sched_cfg.get("queue_limit", 100)))
            queue.start()
            recovered = queue.recover_pending()
            scheduler = Scheduler(session_factory, queue)
            scheduler.start()
            app.state.worker_queue = queue
            app.state.scheduler = scheduler
            app.state.recovered_jobs = recovered

    @app.on_event("shutdown")
    def _shutdown():
        for attr in ("scheduler", "worker_queue"):
            obj = getattr(app.state, attr, None)
            if obj is not None:
                try:
                    obj.stop()
                except Exception:
                    pass

    return app


# Module-level default app instance. Imported by main.py and tests.
# Background threads are started lazily via `enable_background_workers()` so
# that TestClient usage stays deterministic.
app = create_api_app(start_background=False)


def enable_background_workers(target=None):
    """Start worker queue + scheduler on an app (used by the production entry point)."""
    target = target or app
    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    from lifeops.scheduler.worker import Scheduler, WorkerQueue
    queue = WorkerQueue(session_factory)
    queue.start()
    queue.recover_pending()
    scheduler = Scheduler(session_factory, queue)
    scheduler.start()
    target.state.worker_queue = queue
    target.state.scheduler = scheduler
    return target
