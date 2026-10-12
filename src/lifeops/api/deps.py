"""Shared API dependencies: DB session, auth middleware wiring, emergency stop."""
import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from lifeops.storage.database import get_engine, get_session_factory

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Optional test override: when set, get_db builds sessions from this factory.
_TEST_SESSION_FACTORY = None


def set_test_session_factory(factory=None):
    """Install (or clear with None) a session factory used by get_db."""
    global _TEST_SESSION_FACTORY
    _TEST_SESSION_FACTORY = factory


def get_db() -> DBSession:
    if _TEST_SESSION_FACTORY is not None:
        session_factory = _TEST_SESSION_FACTORY
    else:
        engine = get_engine()
        session_factory = get_session_factory(engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Emergency stop (spec section 13): a process-wide flag checked by every
# mutating endpoint and by the agent orchestrator before executing actions.
# ---------------------------------------------------------------------------

class EmergencyStopState:
    def __init__(self):
        self.active = False
        self.reason: Optional[str] = None
        self.since: Optional[datetime.datetime] = None

    def engage(self, reason: str = "manual"):
        self.active = True
        self.reason = reason
        self.since = datetime.datetime.utcnow()

    def release(self):
        self.active = False
        self.reason = None
        self.since = None

    def snapshot(self):
        return {"active": self.active, "reason": self.reason,
                "since": self.since.isoformat() if self.since else None}


emergency_stop = EmergencyStopState()


def require_not_stopped(request: Request):
    """Dependency that returns 423 Locked while emergency stop is engaged."""
    if emergency_stop.active:
        raise HTTPException(status_code=423,
                            detail=f"Emergency stop is active ({emergency_stop.reason}). "
                                   "Release it from the Security page to resume operations.")


# ---------------------------------------------------------------------------
# Auth middleware support (spec sections 8/13). When security.auth_enabled is
# true, all /api/v1 routes except health/login require a valid session cookie.
# ---------------------------------------------------------------------------

PUBLIC_API_PATHS = {"/api/v1/system/health", "/api/v1/auth/login", "/api/v1/auth/status", "/api/v1/auth/bootstrap"}


def auth_enabled(db: DBSession) -> bool:
    from lifeops.services.settings_service import SettingsService
    try:
        return bool(SettingsService(db).get_section("security").get("auth_enabled"))
    except Exception:
        return False


def current_user_from_request(request: Request, db: DBSession) -> Optional[dict]:
    from lifeops.security.auth import validate_session
    sid = request.cookies.get("lifeops_session")
    if not sid:
        return None
    user = validate_session(db, sid)
    if user is None:
        return None
    return {"id": user.id, "username": user.username, "role": user.role}
