from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import pytest
from lifeops.database import Base, Task, AuditEvent
from lifeops.services import (
    ValidationError, create_task, list_tasks, complete_task, create_note,
    create_project, create_memory, search_memories, create_approval,
    decide_approval, create_agent_run, create_self_goal, create_evaluation_record, create_improvement_proposal, decide_improvement_proposal,
)
from lifeops.policy import Decision, decide

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try: yield session
    finally: session.close(); engine.dispose()

def test_task_create_complete_and_audit(db):
    task = create_task(db, "  Ship release ", "check docs", "high")
    assert task.title == "Ship release"
    assert list_tasks(db)[0].id == task.id
    complete_task(db, task.id)
    assert db.get(Task, task.id).status == "completed"
    assert db.scalars(select(AuditEvent)).all()

def test_invalid_task_rejected(db):
    with pytest.raises(ValidationError): create_task(db, " ", priority="medium")
    with pytest.raises(ValidationError): create_task(db, "valid", priority="urgent")

def test_project_and_memory_search(db):
    project = create_project(db, "Personal OS", "Roadmap")
    task = create_task(db, "Implement memory", project_id=project.id)
    assert task.project_id == project.id
    create_memory(db, "Prefers local-first software", "preference")
    assert len(search_memories(db, "local-first")) == 1
    assert search_memories(db, "missing") == []

def test_approval_is_single_decision(db):
    item = create_approval(db, "delete_file", "Delete selected file", "high")
    decide_approval(db, item.id, approve=True, actor="user", reason="reviewed")
    with pytest.raises(ValidationError):
        decide_approval(db, item.id, approve=False, actor="user")
    assert item.status == "approved"

def test_agent_run_does_not_fake_execution(db):
    run = create_agent_run(db, "Research my project")
    assert run.status == "needs_input"
    assert "not configured" in run.error

def test_policy_hard_blocks_and_approval():
    assert decide("disable_authentication", autonomy="bounded").decision == Decision.BLOCK
    assert decide("delete_file", autonomy="bounded").decision == Decision.ASK
    assert decide("create_task", autonomy="supervised").decision == Decision.ALLOW

def test_selfx_records_and_approval_stops_at_trial(db):
    goal = create_self_goal(db, "Improve retrieval", "Raise test relevance", "0.60", "0.80")
    assert goal.status == "active"
    evaluation = create_evaluation_record(db, "retrieval-suite", "v1", score=0.75, details="fixed fixture")
    assert evaluation.score == 0.75
    proposal = create_improvement_proposal(db, "Tune ranking", "Low relevance", "Fixture scores", "Higher recall", "low", "Revert ranking config")
    decide_improvement_proposal(db, proposal.id, approve=True, reason="test evidence reviewed")
    assert proposal.status == "approved_for_trial"
    assert "deployed" not in proposal.status

def test_evaluation_rejects_invalid_score(db):
    with pytest.raises(ValidationError):
        create_evaluation_record(db, "suite", "v1", score=1.5)
