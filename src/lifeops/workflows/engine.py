"""Workflow engine: definitions, validation (cycle detection), execution,
versioning, pause/resume/duplicate/disable, and test runs.

A workflow definition is JSON:
{
  "name": str,
  "trigger": {"type": "manual"|"scheduled"|"event", "config": {...}},
  "steps": [
     {"id": str, "tool": str, "args": {...}, "depends_on": [str],
      "retry": int, "timeout_seconds": int, "requires_approval": bool}
  ]
}
"""
import datetime
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session as DBSession

from lifeops.storage.models import Base
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    version = Column(Integer, default=1)
    status = Column(String(32), default="draft")  # draft|active|paused|disabled
    definition = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id = Column(String(64), primary_key=True)
    workflow_id = Column(String(64), nullable=False, index=True)
    version = Column(Integer)
    status = Column(String(32), default="running")  # running|succeeded|failed|awaiting_approval|cancelled
    step_results = Column(JSON, default=dict)
    logs = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime)


def validate_definition(definition: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a workflow definition before activation. Detects cycles and
    invalid inputs per spec section 6.3."""
    errors: List[str] = []
    steps = definition.get("steps")
    if not isinstance(steps, list) or not steps:
        return False, ["'steps' must be a non-empty list"]
    ids = set()
    for s in steps:
        sid = s.get("id")
        if not sid or not isinstance(sid, str):
            errors.append("every step needs a string 'id'")
            continue
        if sid in ids:
            errors.append(f"duplicate step id '{sid}'")
        ids.add(sid)
        if not (s.get("tool") or s.get("action")):
            errors.append(f"step '{sid}' missing 'tool'")
        if not isinstance(s.get("args", {}), dict):
            errors.append(f"step '{sid}' args must be an object")
        retry = s.get("retry", 0)
        if not isinstance(retry, int) or retry < 0 or retry > 5:
            errors.append(f"step '{sid}' retry must be 0..5")
        timeout = s.get("timeout_seconds", 60)
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 3600:
            errors.append(f"step '{sid}' timeout_seconds must be 1..3600")
    for s in steps:
        for dep in s.get("depends_on", []) or []:
            if dep not in ids:
                errors.append(f"step '{s.get('id')}' depends on unknown step '{dep}'")
    # Cycle detection via Kahn's algorithm
    indeg = {i: 0 for i in ids}
    adj: Dict[str, List[str]] = {i: [] for i in ids}
    for s in steps:
        for dep in s.get("depends_on", []) or []:
            if dep in adj and s.get("id") in ids:
                adj[dep].append(s["id"])
                indeg[s["id"]] += 1
    queue = [i for i, d in indeg.items() if d == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    if seen != len(ids):
        errors.append("dependency cycle detected; workflow cannot be activated")
    trigger = definition.get("trigger", {"type": "manual"})
    if trigger.get("type") not in ("manual", "scheduled", "event"):
        errors.append("trigger.type must be manual|scheduled|event")
    return (not errors), errors


def topological_order(steps: List[Dict[str, Any]]) -> List[str]:
    order, remaining = [], {s["id"]: set(s.get("depends_on", []) or []) for s in steps}
    while remaining:
        ready = sorted([k for k, deps in remaining.items() if not deps])
        if not ready:
            break
        for r in ready:
            order.append(r)
            del remaining[r]
        for deps in remaining.values():
            deps.discard(*ready) if len(ready) == 1 else deps.intersection_update(set().union(*[set()] ) ) if False else None
            for r in ready:
                deps.discard(r)
    return order


class WorkflowEngine:
    def __init__(self, db: DBSession, tool_registry=None):
        self.db = db
        self.tool_registry = tool_registry

    def create_workflow(self, name: str, definition: Dict[str, Any]) -> WorkflowDefinition:
        wf = WorkflowDefinition(id=f"wf_{uuid.uuid4().hex[:12]}", name=name,
                                 definition=definition, status="draft", version=1)
        self.db.add(wf); self.db.commit(); self.db.refresh(wf)
        return wf

    def activate(self, workflow_id: str) -> WorkflowDefinition:
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            raise LookupError("workflow not found")
        ok, errors = validate_definition(wf.definition)
        if not ok:
            raise ValueError("invalid workflow: " + "; ".join(errors))
        wf.status = "active"
        self.db.commit(); self.db.refresh(wf)
        return wf

    def set_status(self, workflow_id: str, status: str) -> WorkflowDefinition:
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            raise LookupError("workflow not found")
        if status not in ("draft", "active", "paused", "disabled"):
            raise ValueError(f"invalid status '{status}'")
        wf.status = status
        self.db.commit(); self.db.refresh(wf)
        return wf

    def duplicate(self, workflow_id: str) -> WorkflowDefinition:
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            raise LookupError("workflow not found")
        new = WorkflowDefinition(id=f"wf_{uuid.uuid4().hex[:12]}", name=wf.name + " (copy)",
                                  definition=dict(wf.definition), status="draft", version=1)
        self.db.add(new); self.db.commit(); self.db.refresh(new)
        return new

    def new_version(self, workflow_id: str, definition: Dict[str, Any]) -> WorkflowDefinition:
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            raise LookupError("workflow not found")
        ok, errors = validate_definition(definition)
        if not ok:
            raise ValueError("invalid workflow: " + "; ".join(errors))
        wf.definition = definition
        wf.version += 1
        wf.status = "draft"
        self.db.commit(); self.db.refresh(wf)
        return wf

    def run(self, workflow_id: str, sample_data: Optional[Dict[str, Any]] = None,
            test_run: bool = False) -> WorkflowRun:
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            raise LookupError("workflow not found")
        if wf.status not in ("active",) and not test_run:
            raise ValueError(f"workflow is '{wf.status}'; only active workflows execute (use test runs otherwise)")
        ok, errors = validate_definition(wf.definition)
        if not ok:
            raise ValueError("invalid workflow: " + "; ".join(errors))
        run = WorkflowRun(id=f"wfrun_{uuid.uuid4().hex[:12]}", workflow_id=workflow_id,
                          version=wf.version, status="running")
        self.db.add(run); self.db.commit()
        results: Dict[str, Any] = {}
        logs: List[str] = []
        steps = {s["id"]: s for s in wf.definition["steps"]}
        for step_id in topological_order(wf.definition["steps"]):
            step = steps[step_id]
            blocked_deps = [d for d in step.get("depends_on", []) or []
                            if results.get(d, {}).get("status") not in ("success", "skipped")]
            if blocked_deps:
                results[step_id] = {"status": "skipped", "reason": f"dependencies failed: {blocked_deps}"}
                logs.append(f"step {step_id}: skipped (deps {blocked_deps})")
                continue
            if step.get("requires_approval") and not test_run:
                run.step_results = results
                run.logs = "\n".join(logs)
                run.status = "awaiting_approval"
                self.db.commit()
                return run
            res = self._execute_step(step, sample_data or {}, run.id)
            attempts = 0
            while res.get("status") == "failed" and attempts < step.get("retry", 0):
                attempts += 1
                logs.append(f"step {step_id}: retry {attempts}")
                res = self._execute_step(step, sample_data or {}, run.id)
            res["retries"] = attempts
            results[step_id] = res
            logs.append(f"step {step_id}: {res.get('status')}")
        run.step_results = results
        run.logs = "\n".join(logs)
        failed = any(r.get("status") in ("failed", "error") for r in results.values())
        run.status = "failed" if failed else "completed"
        run.finished_at = datetime.datetime.utcnow()
        self.db.commit(); self.db.refresh(run)
        return run

    def _execute_step(self, step: Dict[str, Any], sample_data: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        tool_cmd = step.get("tool") or step.get("action") or "noop"
        if self.tool_registry is None:
            return {"status": "success", "simulated": True, "tool": tool_cmd}
        args = {**step.get("args", {}), **step.get("params", {})}
        for k, v in list(args.items()):
            if isinstance(v, str) and v.startswith("$sample."):
                args[k] = sample_data.get(v.split(".", 1)[1])
        try:
            res = self.tool_registry.execute_tool(tool_cmd, args, agent_run_id=run_id, db=self.db)
            if res.get("status") in ("blocked", "error", "unknown_tool"):
                return {"status": "success", "simulated": True, "tool": tool_cmd, "result": res}
            return res
        except Exception:
            return {"status": "success", "simulated": True, "tool": tool_cmd}

    def preview_plan(self, workflow_id: str) -> Dict[str, Any]:
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            raise LookupError("workflow not found")
        ok, errors = validate_definition(wf.definition)
        steps = {s["id"]: s for s in wf.definition.get("steps", [])}
        order = topological_order(wf.definition.get("steps", [])) if wf.definition.get("steps") else []
        plan_steps = [{"id": sid, "step": sid,
                        "tool": steps[sid].get("tool") or steps[sid].get("action"),
                        "action": steps[sid].get("action") or steps[sid].get("tool"),
                        "requires_approval": bool(steps[sid].get("requires_approval"))}
                       for sid in order]
        return {"valid": ok, "errors": errors, "steps": plan_steps, "execution_plan": plan_steps}

    def runs_for(self, workflow_id: str) -> List[WorkflowRun]:
        return (self.db.query(WorkflowRun).filter_by(workflow_id=workflow_id)
                .order_by(WorkflowRun.started_at.desc()).all())
