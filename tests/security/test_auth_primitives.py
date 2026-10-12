import pytest
from lifeops.security.auth import hash_password, verify_password, new_session_token, token_digest, session_expiry

def test_password_hash_round_trip_and_unique_salts():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first.encoded != second.encoded
    assert verify_password("correct horse battery staple", first.encoded)
    assert not verify_password("incorrect password", first.encoded)

def test_password_length_is_enforced():
    with pytest.raises(ValueError):
        hash_password("short")

def test_session_tokens_are_random_and_stored_as_digests():
    token = new_session_token()
    assert len(token) >= 40
    assert token_digest(token) != token
    assert token_digest(token) == token_digest(token)
    assert session_expiry(100) == 100 + 12 * 60 * 60

def test_malformed_hash_fails_closed():
    assert not verify_password("anything", "plaintext")
