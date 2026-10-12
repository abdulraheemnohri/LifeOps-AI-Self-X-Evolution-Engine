import hashlib
import hmac
import secrets
import datetime
from typing import Optional
from sqlalchemy.orm import Session as DBSession
from lifeops.storage.models import User, Session

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${hashed.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, stored_hash = password_hash.split("$")
        recalculated = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return hmac.compare_digest(stored_hash, recalculated)
    except Exception:
        return False

def create_session(db: DBSession, user_id: int, duration_hours: int = 24) -> Session:
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=duration_hours)
    session_obj = Session(id=session_id, user_id=user_id, expires_at=expires_at)
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj

def validate_session(db: DBSession, session_id: str) -> Optional[User]:
    session_obj = db.query(Session).filter_by(id=session_id, revoked=False).first()
    if not session_obj:
        return None
    if session_obj.expires_at < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):
        return None
    return db.query(User).filter_by(id=session_obj.user_id).first()

def revoke_session(db: DBSession, session_id: str):
    session_obj = db.query(Session).filter_by(id=session_id).first()
    if session_obj:
        session_obj.revoked = True
        db.commit()
