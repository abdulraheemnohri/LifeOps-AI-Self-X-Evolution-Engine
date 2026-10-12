import pytest
from lifeops.storage.database import get_engine, init_db, get_session_factory
from lifeops.storage.models import TaskStatus, ApprovalDecision
from lifeops.security.policy import PolicyEngine, PolicyDecision, ApprovalGate
from lifeops.tools.registry import ToolRegistry
from lifeops.models.adapters import MockModelAdapter
from lifeops.core.orchestrator import AgentOrchestrator


def test_agent_and_tools_flow(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "hello.txt").write_text("Hello World", encoding="utf-8")

    policy_engine = PolicyEngine()
    approval_gate = ApprovalGate(db)
    tool_reg = ToolRegistry(policy_engine, approval_gate, workspace=workspace)
    orchestrator = AgentOrchestrator(db, tool_reg, MockModelAdapter())

    run = orchestrator.create_agent_run("Read file safely")
    assert run.id.startswith("run_")
    res = orchestrator.execute_step(run.id, "filesystem.read_file", {"filepath": "hello.txt"})
    assert res["status"] == "success"
    assert res["result"] == "Hello World"
    assert run.status == TaskStatus.SUCCEEDED

    # A path outside the workspace must never be readable.
    outside = tmp_path / "private.txt"
    outside.write_text("secret", encoding="utf-8")
    blocked = tool_reg.execute_tool("filesystem.read_file", {"filepath": str(outside)}, run.id, db)
    assert blocked["status"] == "failed"
    assert "workspace" in blocked["error"].lower()

    # Approval requests are queued; the command is not run in the request path.
    run2 = orchestrator.create_agent_run("Run command")
    res2 = orchestrator.execute_step(run2.id, "terminal.execute", {"command": "echo 123"})
    assert res2["status"] == "awaiting_approval"
    assert run2.status == TaskStatus.AWAITING_APPROVAL
    appr_id = res2["approval_id"]
    approval_gate.decide(appr_id, ApprovalDecision.APPROVED, "admin")
    db.close()
    engine.dispose()


def test_ask_policy_without_approval_gate_never_executes(tmp_path):
    registry = ToolRegistry(PolicyEngine(), workspace=tmp_path / "workspace")
    result = registry.execute_tool("terminal.execute", {"argv": ["echo", "unsafe"]}, "run_1")
    assert result["status"] == "awaiting_approval"
    assert "not executed" in result["message"]


def test_filesystem_write_is_confined_to_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    registry = ToolRegistry(PolicyEngine({ "filesystem.write": PolicyDecision.ALLOW }), workspace=workspace)
    safe = registry.execute_tool("filesystem.write_file", {"filepath": "notes/hello.txt", "content": "hello"}, "run_1")
    assert safe["status"] == "success"
    assert (workspace / "notes" / "hello.txt").read_text(encoding="utf-8") == "hello"
    outside = registry.execute_tool("filesystem.write_file", {"filepath": str(tmp_path / "escape.txt"), "content": "bad"}, "run_1")
    assert outside["status"] == "failed"
    assert not (tmp_path / "escape.txt").exists()
