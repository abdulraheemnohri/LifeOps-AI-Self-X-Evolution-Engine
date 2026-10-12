import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lifeops.security.auth import (
    create_session,
    hash_password,
    new_session_token,
    revoke_session,
    token_digest,
    validate_session,
    verify_password,
)
from lifeops.storage.models import Base, Session, User


def test_password_hash_round_trip_and_unique_salts():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first.encoded != second.encoded
    assert verify_password("correct horse battery staple", first.encoded)
    assert not verify_password("incorrect password", first.encoded)


def test_password_length_is_enforced():
    with pytest.raises(ValueError):
        hash_password("short")


def test_session_tokens_are_random_and_digest_is_one_way():
    token = new_session_token()
    assert len(token) >= 40
    assert token_digest(token) != token
    assert token_digest(token) == token_digest(token)


def test_malformed_hash_fails_closed():
    assert not verify_password("anything", "plaintext")


def test_database_stores_only_session_token_digest():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        user = User(username="test-user", password_hash=hash_password("a sufficiently long password").encoded)
        db.add(user)
        db.commit()
        db.refresh(user)

        session_obj = create_session(db, user.id)
        raw_token = session_obj._raw_token
        stored = db.query(Session).one()
        assert stored.id == token_digest(raw_token)
        assert stored.id != raw_token
        assert validate_session(db, raw_token).id == user.id

        revoke_session(db, raw_token)
        assert validate_session(db, raw_token) is None
    engine.dispose()
