import uuid
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session as DBSession
from lifeops.storage.models import AgentRun, AgentStep, ToolCall, TaskStatus, Approval, ApprovalDecision
from lifeops.models.adapters import BaseModelAdapter, MockModelAdapter
from lifeops.tools.registry import ToolRegistry

class AgentOrchestrator:
    def __init__(self, db: DBSession, tool_registry: ToolRegistry, model_adapter: Optional[BaseModelAdapter] = None):
        self.db = db
        self.tool_registry = tool_registry
        self.model_adapter = model_adapter or MockModelAdapter()

    def create_agent_run(self, objective: str) -> AgentRun:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        run = AgentRun(
            id=run_id,
            objective=objective,
            status=TaskStatus.CREATED,
            plan={"steps": [f"Deconstruct objective: {objective}", "Execute permitted tools", "Verify results"]}
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def execute_step(self, run_id: str, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        run = self.db.query(AgentRun).filter_by(id=run_id).first()
        if not run:
            return {"status": "error", "message": "Agent run not found"}

        run.status = TaskStatus.RUNNING
        self.db.commit()

        exec_res = self.tool_registry.execute_tool(
            tool_name=tool_name,
            kwargs=tool_args,
            agent_run_id=run_id,
            db=self.db
        )

        tc = ToolCall(
            agent_run_id=run_id,
            tool_name=tool_name,
            inputs=tool_args,
            outputs=exec_res,
            status=exec_res.get("status", "unknown")
        )
        self.db.add(tc)

        if exec_res.get("status") == "awaiting_approval":
            run.status = TaskStatus.AWAITING_APPROVAL
        elif exec_res.get("status") == "success":
            run.status = TaskStatus.SUCCEEDED
            run.results = exec_res.get("result")
            run.completed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        elif exec_res.get("status") in ["blocked", "failed"]:
            run.status = TaskStatus.FAILED
            run.error = exec_res.get("message") or exec_res.get("error")

        self.db.commit()
        self.db.refresh(run)
        return exec_res
