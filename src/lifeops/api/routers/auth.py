"""Auth & system routers (login/logout/bootstrap, health, identity, emergency stop)."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession

from lifeops.api.deps import (auth_enabled, current_user_from_request, emergency_stop,
                              get_db)
from lifeops.security.auth import (create_session, hash_password, revoke_session,
                                   verify_password)
from lifeops.security.policy import log_audit_event
from lifeops.selfx.engine import SelfDiagnostics, SelfIdentity
from lifeops.storage.models import User

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/system/health")
def health_check(db: DBSession = Depends(get_db)):
    diag = SelfDiagnostics(db)
    result = diag.run_health_check()
    result["emergency_stop"] = emergency_stop.snapshot()
    return result


@router.get("/system/identity")
def get_identity():
    return SelfIdentity.get_system_identity()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@router.get("/auth/status")
def auth_status(request: Request, db: DBSession = Depends(get_db)):
    enabled = auth_enabled(db)
    user = current_user_from_request(request, db) if enabled else None
    users_count = db.query(User).count()
    return {"auth_enabled": enabled, "authenticated": bool(user) or not enabled,
            "user": user, "needs_bootstrap": enabled and users_count == 0}


@router.post("/auth/bootstrap")
def bootstrap_admin(payload: dict, db: DBSession = Depends(get_db)):
    """Create the first admin account when auth is enabled but no users exist."""
    if db.query(User).count() > 0:
        raise HTTPException(status_code=409, detail="Users already exist")
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if len(username) < 3:
        raise HTTPException(status_code=422, detail="username must be at least 3 characters")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    user = User(username=username, password_hash=hash_password(password).encoded, role="admin")
    db.add(user)
    db.commit()
    log_audit_event(db, actor="system", action="auth.bootstrap", target=username, outcome="success")
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/auth/login")
def login(payload: dict, request: Request, response: Response, db: DBSession = Depends(get_db)):
    username = payload.get("username", "")
    password = payload.get("password", "")
    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        log_audit_event(db, actor=username or "anonymous", action="auth.login",
                        target=username, outcome="failure")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_obj = create_session(db, user.id)
    response.set_cookie(key="lifeops_session", value=getattr(session_obj, "_raw_token", session_obj.id), httponly=True, samesite="lax")
    log_audit_event(db, actor=user.username, action="auth.login", target="session", outcome="success")
    return {"status": "ok", "username": user.username, "role": user.role}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    sid = request.cookies.get("lifeops_session")
    if sid:
        revoke_session(db, sid)
    response.delete_cookie("lifeops_session", path="/")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Emergency stop (spec section 13)
# ---------------------------------------------------------------------------

@router.get("/system/emergency-stop")
def get_emergency_stop():
    return emergency_stop.snapshot()


@router.post("/system/emergency-stop/engage")
def engage_emergency_stop(payload: dict = None, db: DBSession = Depends(get_db)):
    reason = (payload or {}).get("reason", "manual")
    emergency_stop.engage(reason)
    log_audit_event(db, actor="user", action="security.emergency_stop.engage",
                    target="system", outcome="success", details={"reason": reason})
    return emergency_stop.snapshot()


@router.post("/system/emergency-stop/release")
def release_emergency_stop(db: DBSession = Depends(get_db)):
    emergency_stop.release()
    log_audit_event(db, actor="user", action="security.emergency_stop.release",
                    target="system", outcome="success")
    return emergency_stop.snapshot()
