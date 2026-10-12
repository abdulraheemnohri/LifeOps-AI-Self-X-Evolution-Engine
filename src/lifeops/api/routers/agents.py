"""Agent, assistant, tools, models, and integrations routers."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from lifeops.api.deps import get_db, require_not_stopped
from lifeops.api.helpers import paged, raise_lookup, raise_value
from lifeops.core.orchestrator import AgentOrchestrator
from lifeops.models.adapters import LiteRTLMAdapter, MockModelAdapter, OllamaAdapter
from lifeops.security.policy import ApprovalGate, PolicyEngine, log_audit_event
from lifeops.services import crud
from lifeops.services.settings_service import SettingsService
from lifeops.storage.models import (AgentRun, AgentStep, Approval, ApprovalDecision,
                                    Conversation, Integration, Message, TaskStatus, ToolCall)
from lifeops.tools.registry import ToolRegistry

router = APIRouter(prefix="/api/v1", tags=["agents"], dependencies=[Depends(require_not_stopped)])


def _registry(db: DBSession) -> ToolRegistry:
    return ToolRegistry(PolicyEngine(), ApprovalGate(db))


def _get_adapter(settings: dict):
    model_cfg = settings.get("model", {})
    runtime = model_cfg.get("runtime", "mock")
    model_path = model_cfg.get("model_path") or None
    if runtime == "ollama":
        return OllamaAdapter(
            model_name=model_path or "llama3.2",
            base_url=model_cfg.get("ollama_base_url") or None,
            generation_params=model_cfg.get("generation_params"),
        )
    if runtime == "litert" and model_path:
        return LiteRTLMAdapter(model_path=model_path)
    if runtime == "litert":
        return LiteRTLMAdapter()
    return MockModelAdapter()


# ---------------------------------------------------------------------------
# Assistant chat (conversations + messages)
# ---------------------------------------------------------------------------

@router.get("/assistant/conversations")
def list_conversations(db: DBSession = Depends(get_db)):
    convs = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    return [crud.to_dict(c) for c in convs]


@router.post("/assistant/conversations")
def create_conversation(payload: dict, db: DBSession = Depends(get_db)):
    conv = Conversation(title=payload.get("title", "New Conversation"))
    db.add(conv); db.commit(); db.refresh(conv)
    return crud.to_dict(conv)


@router.get("/assistant/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, db: DBSession = Depends(get_db)):
    try:
        crud.get_or_404(db, Conversation, conversation_id)
    except LookupError as exc:
        raise_lookup(exc)
    msgs = db.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.id).all()
    return {"conversation_id": conversation_id, "messages": [crud.to_dict(m) for m in msgs]}


@router.post("/assistant/message")
def send_message(payload: dict, db: DBSession = Depends(get_db)):
    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="'content' is required")
    conversation_id = payload.get("conversation_id")
    if conversation_id:
        try:
            conv = crud.get_or_404(db, Conversation, conversation_id)
        except LookupError as exc:
            raise_lookup(exc)
    else:
        conv = Conversation(title=content[:80])
        db.add(conv); db.commit()
    db.add(Message(conversation_id=conv.id, role="user", content=content))
    adapter = _get_adapter(SettingsService(db).get_all())
    reply = adapter.generate(content)
    msg = Message(conversation_id=conv.id, role="assistant", content=reply)
    db.add(msg); db.commit(); db.refresh(msg)
    return {"conversation_id": conv.id, "message": crud.to_dict(msg)}


# ---------------------------------------------------------------------------
# Agent runs
# ---------------------------------------------------------------------------

@router.get("/agents/runs")
def list_runs(status: Optional[str] = None, page: int = 1, page_size: int = 50,
              db: DBSession = Depends(get_db)):
    q = db.query(AgentRun)
    if status:
        q = q.filter(AgentRun.status == TaskStatus(status.upper()))
    result = crud.paginate(q.order_by(AgentRun.created_at.desc()), page, page_size)
    return paged(result, lambda r: crud.to_dict(r))


@router.post("/agents/runs")
def create_run(payload: dict, db: DBSession = Depends(get_db)):
    objective = (payload.get("objective") or "").strip()
    if not objective:
        raise HTTPException(status_code=422, detail="'objective' is required")
    orch = AgentOrchestrator(db, _registry(db), _get_adapter(SettingsService(db).get_all()))
    run = orch.create_agent_run(objective)
    log_audit_event(db, actor="user", action="agent.run.create",
                    target=f"AgentRun:{run.id}", outcome="success")
    return crud.to_dict(run)


@router.get("/agents/runs/{run_id}")
def get_run(run_id: str, db: DBSession = Depends(get_db)):
    try:
        run = crud.get_or_404(db, AgentRun, run_id)
    except LookupError as exc:
        raise_lookup(exc)
    steps = db.query(AgentStep).filter_by(agent_run_id=run_id).all()
    calls = db.query(ToolCall).filter_by(agent_run_id=run_id).all()
    data = crud.to_dict(run)
    data["steps"] = [crud.to_dict(s) for s in steps]
    data["tool_calls"] = [crud.to_dict(c) for c in calls]
    return data


@router.post("/agents/runs/{run_id}/execute")
def execute_step(run_id: str, payload: dict, db: DBSession = Depends(get_db)):
    orch = AgentOrchestrator(db, _registry(db))
    tool_name = payload.get("tool", "")
    args = payload.get("args", {}) or {}
    result = orch.execute_step(run_id, tool_name, args)
    return {"run_id": run_id, "result": result}


@router.post("/agents/runs/{run_id}/cancel")
def cancel_run(run_id: str, db: DBSession = Depends(get_db)):
    try:
        run = crud.get_or_404(db, AgentRun, run_id)
    except LookupError as exc:
        raise_lookup(exc)
    run.status = TaskStatus.CANCELLED
    run.completed_at = __import__("datetime").datetime.utcnow()
    db.commit()
    log_audit_event(db, actor="user", action="agent.run.cancel",
                    target=f"AgentRun:{run_id}", outcome="success")
    return crud.to_dict(run)


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

@router.get("/approvals")
def list_approvals(decision: Optional[str] = None, db: DBSession = Depends(get_db)):
    q = db.query(Approval)
    if decision:
        q = q.filter(Approval.decision == ApprovalDecision(decision.upper()))
    else:
        q = q.filter(Approval.decision == ApprovalDecision.PENDING)
    return [crud.to_dict(a) for a in q.order_by(Approval.id).all()]


@router.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, payload: dict, db: DBSession = Depends(get_db)):
    gate = ApprovalGate(db)
    decision_str = payload.get("decision", "APPROVED").upper()
    if decision_str not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=422, detail="decision must be APPROVED or REJECTED")
    decision = ApprovalDecision.APPROVED if decision_str == "APPROVED" else ApprovalDecision.REJECTED
    if not gate.decide(approval_id, decision, payload.get("decided_by", "user")):
        raise_lookup(LookupError("Approval request not found"))
    log_audit_event(db, actor=payload.get("decided_by", "user"), action="approval.decision",
                    target=approval_id, outcome="success", details={"decision": decision.value})
    return {"status": "success", "approval_id": approval_id, "decision": decision.value}


# ---------------------------------------------------------------------------
# Tools & policy
# ---------------------------------------------------------------------------

@router.get("/tools")
def list_tools(db: DBSession = Depends(get_db)):
    reg = _registry(db)
    return [{"name": t["name"], "category": t["category"], "action_key": t["action_key"],
             "description": t["description"]} for t in reg.tools.values()]


@router.post("/tools/execute")
def execute_tool(request: Request, payload: dict, db: DBSession = Depends(get_db)):
    tool_name = payload.get("tool", "")
    args = payload.get("args", {}) or {}
    run_id = payload.get("agent_run_id") or f"adhoc_{uuid.uuid4().hex[:8]}"
    registry = getattr(request.app.state, "tool_registry", None) or _registry(db)
    result = registry.execute_tool(tool_name, args, agent_run_id=run_id, db=db)
    log_audit_event(db, actor="agent", action="tool.execute", target=tool_name,
                    outcome=result.get("status", "unknown"))
    return result


@router.get("/policy")
def get_policy(db: DBSession = Depends(get_db)):
    overrides = SettingsService(db).get_autonomy_profile().get("policy_overrides", {})
    engine = PolicyEngine({k: __import__("lifeops.security.policy", fromlist=["PolicyDecision"]).PolicyDecision(v)
                           for k, v in overrides.items()})
    return {"policies": {k: v.value for k, v in engine.policies.items()},
            "autonomy_profile": SettingsService(db).get_autonomy_profile()}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@router.get("/models/runtime")
def model_runtime(db: DBSession = Depends(get_db)):
    import shutil
    settings = SettingsService(db).get_all()
    model_cfg = settings.get("model", {})
    binary = shutil.which("litert-lm")
    ollama_url = model_cfg.get("ollama_base_url") or OllamaAdapter.DEFAULT_BASE_URL
    ollama_reachable = OllamaAdapter(base_url=ollama_url).is_available()
    available_runtimes = ["mock"]
    if binary:
        available_runtimes.append("litert")
    if ollama_reachable:
        available_runtimes.append("ollama")
    return {"configured_runtime": model_cfg.get("runtime"),
            "litert_binary_found": bool(binary),
            "litert_binary_path": binary,
            "ollama_base_url": ollama_url,
            "ollama_reachable": ollama_reachable,
            "available_runtimes": available_runtimes,
            "model_path": model_cfg.get("model_path"),
            "generation_params": model_cfg.get("generation_params"),
            "note": ("Set model.runtime to 'mock', 'litert' (needs litert-lm binary + model_path) "
                     "or 'ollama' (needs a running Ollama server; model_path = model name).")}


@router.post("/models/test")
def test_model(payload: dict, db: DBSession = Depends(get_db)):
    prompt = payload.get("prompt", "ping")
    adapter = _get_adapter(SettingsService(db).get_all())
    try:
        response = adapter.generate(prompt)
        error = None
    except Exception as exc:
        response = None
        error = str(exc)
    return {"runtime": type(adapter).__name__,
            "available": adapter.is_available(),
            "response": response,
            "error": error}


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------

@router.get("/integrations")
def list_integrations(db: DBSession = Depends(get_db)):
    rows = db.query(Integration).all()
    return [crud.to_dict(i) for i in rows]


@router.post("/integrations")
def register_integration(payload: dict, db: DBSession = Depends(get_db)):
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="'name' is required")
    integ_id = payload.get("id") or f"int_{uuid.uuid4().hex[:10]}"
    row = Integration(id=integ_id, name=name, enabled=bool(payload.get("enabled", False)),
                      config=payload.get("config", {}) or {}, health_status="unknown")
    db.add(row); db.commit(); db.refresh(row)
    return crud.to_dict(row)


@router.patch("/integrations/{integration_id}")
def update_integration(integration_id: str, payload: dict, db: DBSession = Depends(get_db)):
    try:
        row = crud.get_or_404(db, Integration, integration_id)
    except LookupError as exc:
        raise_lookup(exc)
    allowed = {k: v for k, v in payload.items() if k in ("name", "enabled", "config", "health_status")}
    return crud.to_dict(crud.apply_update(db, row, allowed, action="integration.update"))


@router.delete("/integrations/{integration_id}")
def delete_integration(integration_id: str, db: DBSession = Depends(get_db)):
    row = crud.get_or_404(db, Integration, integration_id)
    crud.delete_object(db, row, action="integration.delete")
    return {"status": "deleted", "id": integration_id}
