"""Local authentication primitives backed by SQLAlchemy user/session records."""
from __future__ import annotations
import datetime, hashlib, hmac, secrets
from typing import Optional
from sqlalchemy.orm import Session as DBSession
from lifeops.storage.models import User, Session

PBKDF2_ROUNDS = 310_000
MAX_PASSWORD_LENGTH = 1024

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not isinstance(password, str) or not 12 <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError("Password must be between 12 and 1,024 characters.")
    salt_value = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_value.encode("utf-8"), PBKDF2_ROUNDS)
    return f"pbkdf2_sha256$\u007bPBKDF2_ROUNDS\u007d$\u007bsalt_value\u007d$\u007bderived.hex()\u007d"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, rounds_text, salt, stored_hash = password_hash.split("$", 3)
        rounds = int(rounds_text)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= rounds <= 2_000_000: return False
        if not isinstance(password, str) or len(password) > MAX_PASSWORD_LENGTH: return False
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds).hex()
        return hmac.compare_digest(stored_hash, derived)
    except (ValueError, TypeError, AttributeError, UnicodeError):
        return False

def create_session(db: DBSession, user_id: int, duration_hours: int = 12) -> Session:
    if not 1 <= duration_hours <= 24: raise ValueError("Session duration must be between 1 and 24 hours.")
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=duration_hours)
    session_obj = Session(id=session_id, user_id=user_id, expires_at=expires_at)
    db.add(session_obj); db.commit(); db.refresh(session_obj)
    return session_obj

def validate_session(db: DBSession, session_id: str) -> Optional[User]:
    if not session_id or len(session_id) > 256: return None
    session_obj = db.query(Session).filter_by(id=session_id, revoked=False).first()
    if not session_obj: return None
    if session_obj.expires_at < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None): return None
    return db.query(User).filter_by(id=session_obj.user_id).first()

def revoke_session(db: DBSession, session_id: str) -> None:
    session_obj = db.query(Session).filter_by(id=session_id).first()
    if session_obj and not session_obj.revoked:
        session_obj.revoked = True
        db.commit()
