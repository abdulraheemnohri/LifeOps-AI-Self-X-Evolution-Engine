"""Local authentication primitives: PBKDF2 password hashes and opaque sessions."""
from __future__ import annotations

import datetime
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from lifeops.storage.models import User, Session

PBKDF2_ROUNDS = 310_000
MIN_PBKDF2_ROUNDS = 100_000
MAX_PBKDF2_ROUNDS = 2_000_000
MAX_PASSWORD_LENGTH = 1024
SESSION_TTL_SECONDS = 12 * 60 * 60

@dataclass(frozen=True)
class PasswordHash:
    encoded: str

def hash_password(password: str, salt: Optional[str] = None) -> PasswordHash:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random per-password salt."""
    if not isinstance(password, str) or not 12 <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError("Password must be between 12 and 1,024 characters.")
    salt_value = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_value.encode("utf-8"), PBKDF2_ROUNDS)
    encoded = "pbkdf2_sha256$" + str(PBKDF2_ROUNDS) + "$" + salt_value + "$" + derived.hex()
    return PasswordHash(encoded=encoded)

def verify_password(password: str, password_hash: str | PasswordHash) -> bool:
    """Verify a serialized hash; malformed or unsupported hashes fail closed."""
    try:
        encoded = password_hash.encoded if isinstance(password_hash, PasswordHash) else password_hash
        if not isinstance(encoded, str) or not isinstance(password, str) or len(password) > MAX_PASSWORD_LENGTH:
            return False
        algorithm, rounds_text, salt, stored_hash = encoded.split("$", 3)
        rounds = int(rounds_text)
        if algorithm != "pbkdf2_sha256" or not MIN_PBKDF2_ROUNDS <= rounds <= MAX_PBKDF2_ROUNDS:
            return False
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds).hex()
        return hmac.compare_digest(stored_hash, derived)
    except (ValueError, TypeError, AttributeError, UnicodeError):
        return False

def new_session_token() -> str:
    """Create a high-entropy opaque bearer token; persist only its digest."""
    return secrets.token_urlsafe(32)

def token_digest(token: str) -> str:
    if not isinstance(token, str) or not token or len(token) > 512:
        raise ValueError("Invalid session token.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def session_expiry(now: float | None = None, ttl_seconds: int = SESSION_TTL_SECONDS) -> float:
    import time
    if not 1 <= ttl_seconds <= 24 * 60 * 60:
        raise ValueError("Session lifetime must be between 1 second and 24 hours.")
    return (time.time() if now is None else now) + ttl_seconds

def create_session(db: DBSession, user_id: int, duration_hours: int = 12) -> Session:
    if not 1 <= duration_hours <= 24:
        raise ValueError("Session duration must be between 1 and 24 hours.")
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=duration_hours)
    session_obj = Session(id=session_id, user_id=user_id, expires_at=expires_at)
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj

def validate_session(db: DBSession, session_id: str) -> Optional[User]:
    if not session_id or len(session_id) > 256:
        return None
    session_obj = db.query(Session).filter_by(id=session_id, revoked=False).first()
    if not session_obj or session_obj.expires_at < datetime.datetime.utcnow():
        return None
    return db.query(User).filter_by(id=session_obj.user_id).first()

def revoke_session(db: DBSession, session_id: str) -> None:
    session_obj = db.query(Session).filter_by(id=session_id).first()
    if session_obj and not session_obj.revoked:
        session_obj.revoked = True
        db.commit()
