"""Authentication service layer for user management and session handling."""
import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from lifeops.storage.models import User, Session
from lifeops.security.auth import (
    hash_password, verify_password, create_session, validate_session,
    revoke_session, token_digest, SESSION_TTL_SECONDS
)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: DBSession):
        self.db = db

    def create_user(self, username: str, password: str, role: str = "user") -> Tuple[bool, str, Optional[User]]:
        """Create a new user."""
        # Check if username exists
        existing = self.db.scalar(select(User).where(User.username == username))
        if existing:
            return False, "Username already exists", None
        
        # Validate username
        if not username or len(username) < 3 or len(username) > 64:
            return False, "Username must be between 3 and 64 characters", None
        
        # Validate password
        if not password or len(password) < 12:
            return False, "Password must be at least 12 characters", None
        
        try:
            password_hash = hash_password(password)
            user = User(username=username, password_hash=password_hash.encoded, role=role)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return True, "User created successfully", user
        except Exception as e:
            self.db.rollback()
            return False, str(e), None

    def authenticate_user(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Authenticate a user and return the user object if successful."""
        user = self.db.scalar(select(User).where(User.username == username))
        if not user:
            return False, "Invalid username or password", None
        
        if not verify_password(password, user.password_hash):
            return False, "Invalid username or password", None
        
        return True, "Authentication successful", user

    def create_session(self, user_id: int, duration_hours: int = 12) -> Tuple[bool, str, Optional[Session]]:
        """Create a new session for a user."""
        user = self.db.get(User, user_id)
        if not user:
            return False, "User not found", None
        
        try:
            session = create_session(self.db, user_id, duration_hours)
            return True, "Session created", session
        except Exception as e:
            return False, str(e), None

    def validate_session(self, session_id: str) -> Optional[User]:
        """Validate a session and return the associated user."""
        return validate_session(self.db, session_id)

    def revoke_session(self, session_id: str) -> Tuple[bool, str]:
        """Revoke a session."""
        try:
            revoke_session(self.db, session_id)
            return True, "Session revoked"
        except Exception as e:
            return False, str(e)

    def revoke_all_user_sessions(self, user_id: int) -> Tuple[bool, str]:
        """Revoke all sessions for a user."""
        try:
            sessions = self.db.scalars(
                select(Session).where(Session.user_id == user_id)
            ).all()
            for session in sessions:
                session.revoked = True
            self.db.commit()
            return True, f"Revoked {len(sessions)} sessions"
        except Exception as e:
            return False, str(e)

    def list_users(self) -> list[User]:
        """List all users."""
        return self.db.scalars(select(User).order_by(User.username)).all()

    def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return self.db.get(User, user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self.db.scalar(select(User).where(User.username == username))

    def update_user(self, user_id: int, updates: dict) -> Tuple[bool, str, Optional[User]]:
        """Update user information."""
        user = self.db.get(User, user_id)
        if not user:
            return False, "User not found", None
        
        for key, value in updates.items():
            if hasattr(user, key) and key != "id":
                setattr(user, key, value)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return True, "User updated", user
        except Exception as e:
            self.db.rollback()
            return False, str(e), None

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """Delete a user."""
        user = self.db.get(User, user_id)
        if not user:
            return False, "User not found"
        
        try:
            # Revoke all sessions first
            self.revoke_all_user_sessions(user_id)
            self.db.delete(user)
            self.db.commit()
            return True, "User deleted"
        except Exception as e:
            self.db.rollback()
            return False, str(e)

    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change a user's password."""
        user = self.db.get(User, user_id)
        if not user:
            return False, "User not found"
        
        # Verify old password
        if not verify_password(old_password, user.password_hash):
            return False, "Old password is incorrect"
        
        # Validate new password
        if not new_password or len(new_password) < 12:
            return False, "New password must be at least 12 characters"
        
        try:
            password_hash = hash_password(new_password)
            user.password_hash = password_hash.encoded
            self.db.commit()
            return True, "Password changed"
        except Exception as e:
            self.db.rollback()
            return False, str(e)

    def cleanup_expired_sessions(self) -> Tuple[int, str]:
        """Clean up expired sessions."""
        now = datetime.datetime.utcnow()
        expired_sessions = self.db.scalars(
            select(Session).where(Session.expires_at < now)
        ).all()
        
        count = 0
        for session in expired_sessions:
            if not session.revoked:
                session.revoked = True
                count += 1
        
        self.db.commit()
        return count, f"Cleaned up {count} expired sessions"

    def get_session_count(self, user_id: int) -> int:
        """Get the number of active sessions for a user."""
        now = datetime.datetime.utcnow()
        return self.db.scalar(
            select(func.count())
            .where(
                Session.user_id == user_id,
                Session.revoked == False,
                Session.expires_at > now
            )
        )

    def get_active_sessions(self) -> list[Session]:
        """Get all active (non-revoked, non-expired) sessions."""
        now = datetime.datetime.utcnow()
        return self.db.scalars(
            select(Session).where(
                Session.revoked == False,
                Session.expires_at > now
            )
        ).all()
