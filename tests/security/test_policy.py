import pytest
from lifeops.storage.database import get_engine, init_db, get_session_factory
from lifeops.storage.models import User, ApprovalDecision, AuditEvent
from lifeops.security.auth import hash_password, verify_password, create_session, validate_session, revoke_session
from lifeops.security.policy import PolicyEngine, PolicyDecision, ApprovalGate, log_audit_event

def test_auth_password_and_session(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    pwd = "secretpassword123"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed)
    assert not verify_password("wrong", hashed)

    user = User(username="alice", password_hash=hashed.encoded)
    db.add(user)
    db.commit()

    sess = create_session(db, user.id)
    raw_token = getattr(sess, "_raw_token", sess.id)
    val_user = validate_session(db, raw_token)
    assert val_user is not None
    assert val_user.username == "alice"

    revoke_session(db, raw_token)
    assert validate_session(db, raw_token) is None
    db.close()

def test_policy_and_approval_gate(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    engine_policy = PolicyEngine()
    assert engine_policy.evaluate("filesystem.read") == PolicyDecision.ALLOW
    assert engine_policy.evaluate("terminal.execute") == PolicyDecision.ASK
    assert engine_policy.evaluate("system.modify") == PolicyDecision.BLOCK

    gate = ApprovalGate(db)
    appr_id = gate.request_approval("run_123", "terminal.execute", "Run ls -la", {"cmd": "ls -la"})
    assert appr_id.startswith("appr_")

    success = gate.decide(appr_id, ApprovalDecision.APPROVED, "admin")
    assert success is True

    log_audit_event(db, "admin", "approval.decide", appr_id, "SUCCESS", {"password": "secret", "note": "approved"})
    audit = db.query(AuditEvent).filter_by(action="approval.decide").first()
    assert audit is not None
    assert audit.details["password"] == "[REDACTED]"
    assert audit.details["note"] == "approved"
    db.close()
