import pytest
from src.lifeops.storage.database import get_engine, init_db, get_session_factory
from src.lifeops.storage.models import TaskStatus, ApprovalDecision
from src.lifeops.security.policy import PolicyEngine, PolicyDecision, ApprovalGate
from src.lifeops.tools.registry import ToolRegistry
from src.lifeops.models.adapters import MockModelAdapter, LiteRTLMAdapter
from src.lifeops.core.orchestrator import AgentOrchestrator

def test_agent_and_tools_flow(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    policy_engine = PolicyEngine()
    approval_gate = ApprovalGate(db)
    tool_reg = ToolRegistry(policy_engine, approval_gate)
    orchestrator = AgentOrchestrator(db, tool_reg, MockModelAdapter())

    # Create run
    run = orchestrator.create_agent_run("Read file safely")
    assert run.id.startswith("run_")

    # Allowed tool call
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello World", encoding="utf-8")

    res = orchestrator.execute_step(run.id, "filesystem.read_file", {"filepath": str(test_file)})
    assert res["status"] == "success"
    assert res["result"] == "Hello World"
    assert run.status == TaskStatus.SUCCEEDED

    # Approval gated tool call
    run2 = orchestrator.create_agent_run("Run command")
    res2 = orchestrator.execute_step(run2.id, "terminal.execute", {"command": "echo 123"})
    assert res2["status"] == "awaiting_approval"
    assert run2.status == TaskStatus.AWAITING_APPROVAL

    # Decide approval
    appr_id = res2["approval_id"]
    approval_gate.decide(appr_id, ApprovalDecision.APPROVED, "admin")

    db.close()
