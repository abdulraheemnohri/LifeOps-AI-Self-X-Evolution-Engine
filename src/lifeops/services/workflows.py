"""Workflow service layer for managing workflows with visual builder support."""
import datetime
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, desc
from sqlalchemy.orm import Session as DBSession

from lifeops.workflows.engine import WorkflowDefinition, WorkflowRun
from lifeops.workflows.engine import WorkflowEngine, validate_definition, topological_order


class WorkflowService:
    """Service layer for workflow management with visual builder support."""

    def __init__(self, db: DBSession):
        self.db = db
        self.engine = WorkflowEngine(db)

    def create_workflow(self, name: str, definition: Dict[str, Any]) -> WorkflowDefinition:
        """Create a new workflow definition."""
        return self.engine.create_workflow(name, definition)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow by ID."""
        return self.db.get(WorkflowDefinition, workflow_id)

    def list_workflows(self, status: Optional[str] = None) -> List[WorkflowDefinition]:
        """List all workflows, optionally filtered by status."""
        query = select(WorkflowDefinition).order_by(desc(WorkflowDefinition.updated_at))
        if status:
            query = query.where(WorkflowDefinition.status == status)
        return self.db.scalars(query).all()

    def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> Optional[WorkflowDefinition]:
        """Update workflow metadata (not definition)."""
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            return None
        for key, value in updates.items():
            if hasattr(wf, key) and key != 'definition':
                setattr(wf, key, value)
        wf.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(wf)
        return wf

    def update_workflow_definition(self, workflow_id: str, definition: Dict[str, Any]) -> Tuple[bool, str]:
        """Update workflow definition with validation."""
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            return False, "Workflow not found"
        
        ok, errors = validate_definition(definition)
        if not ok:
            return False, "; ".join(errors)
        
        wf.definition = definition
        wf.version += 1
        wf.status = "draft"
        wf.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(wf)
        return True, "Workflow updated"

    def activate_workflow(self, workflow_id: str) -> Tuple[bool, str]:
        """Activate a workflow after validation."""
        try:
            self.engine.activate(workflow_id)
            return True, "Workflow activated"
        except LookupError:
            return False, "Workflow not found"
        except ValueError as e:
            return False, str(e)

    def deactivate_workflow(self, workflow_id: str) -> Tuple[bool, str]:
        """Deactivate a workflow."""
        try:
            self.engine.set_status(workflow_id, "disabled")
            return True, "Workflow deactivated"
        except LookupError:
            return False, "Workflow not found"

    def duplicate_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Duplicate a workflow."""
        try:
            return self.engine.duplicate(workflow_id)
        except LookupError:
            return None

    def delete_workflow(self, workflow_id: str) -> Tuple[bool, str]:
        """Delete a workflow."""
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            return False, "Workflow not found"
        self.db.delete(wf)
        self.db.commit()
        return True, "Workflow deleted"

    def run_workflow(self, workflow_id: str, sample_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[WorkflowRun]]:
        """Run a workflow."""
        try:
            run = self.engine.run(workflow_id, sample_data=sample_data)
            return True, f"Workflow run {run.id} started", run
        except LookupError:
            return False, "Workflow not found", None
        except ValueError as e:
            return False, str(e), None

    def test_workflow(self, workflow_id: str, sample_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test run a workflow without requiring active status."""
        try:
            run = self.engine.run(workflow_id, sample_data=sample_data, test_run=True)
            return True, f"Test run {run.id} completed", {
                "run_id": run.id,
                "status": run.status,
                "results": run.step_results,
                "logs": run.logs
            }
        except LookupError:
            return False, "Workflow not found", None
        except ValueError as e:
            return False, str(e), None

    def get_workflow_runs(self, workflow_id: str, limit: int = 20) -> List[WorkflowRun]:
        """Get recent runs for a workflow."""
        return self.engine.runs_for(workflow_id)[:limit]

    def get_all_runs(self, limit: int = 50) -> List[WorkflowRun]:
        """Get all workflow runs."""
        return self.db.scalars(
            select(WorkflowRun).order_by(desc(WorkflowRun.started_at)).limit(limit)
        ).all()

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Get a specific workflow run."""
        return self.db.get(WorkflowRun, run_id)

    def preview_workflow_plan(self, workflow_id: str) -> Dict[str, Any]:
        """Preview the execution plan for a workflow."""
        try:
            return self.engine.preview_plan(workflow_id)
        except LookupError:
            return {"valid": False, "errors": ["Workflow not found"]}

    def validate_workflow_json(self, definition_json: str) -> Tuple[bool, List[str]]:
        """Validate a workflow definition from JSON string."""
        try:
            definition = json.loads(definition_json)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        return validate_definition(definition)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for workflow builder."""
        from lifeops.tools.registry import tool_registry
        tools = []
        for tool_id, tool_info in tool_registry.tools.items():
            tools.append({
                "id": tool_id,
                "name": tool_info.get("name", tool_id),
                "category": tool_info.get("category", "unknown"),
                "description": tool_info.get("description", ""),
                "action_key": tool_info.get("action_key", tool_id),
                "risk_level": tool_info.get("risk_level", "low"),
                "permissions": tool_info.get("permissions", []),
                "enabled": tool_info.get("enabled", True)
            })
        return sorted(tools, key=lambda x: x["name"])

    def create_workflow_from_visual(self, name: str, steps: List[Dict[str, Any]], 
                                     trigger: Dict[str, Any]) -> Tuple[bool, str, Optional[WorkflowDefinition]]:
        """Create a workflow from visual builder data."""
        definition = {
            "name": name,
            "trigger": trigger,
            "steps": steps
        }
        ok, errors = validate_definition(definition)
        if not ok:
            return False, "; ".join(errors), None
        
        try:
            wf = self.create_workflow(name, definition)
            return True, "Workflow created", wf
        except Exception as e:
            return False, str(e), None

    def get_workflow_graph(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow dependency graph for visualization."""
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            return {"nodes": [], "edges": []}
        
        steps = wf.definition.get("steps", [])
        nodes = []
        edges = []
        
        for step in steps:
            step_id = step.get("id", "")
            nodes.append({
                "id": step_id,
                "label": step_id,
                "tool": step.get("tool", ""),
                "requires_approval": step.get("requires_approval", False),
                "retry": step.get("retry", 0),
                "timeout": step.get("timeout_seconds", 60)
            })
            
            for dep in step.get("depends_on", []):
                edges.append({
                    "source": dep,
                    "target": step_id
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }

    def get_workflow_builder_data(self, workflow_id: str) -> Dict[str, Any]:
        """Get data needed for visual workflow builder."""
        wf = self.db.get(WorkflowDefinition, workflow_id)
        if not wf:
            return {"error": "Workflow not found"}
        
        return {
            "workflow": {
                "id": wf.id,
                "name": wf.name,
                "version": wf.version,
                "status": wf.status,
                "definition": wf.definition
            },
            "available_tools": self.get_available_tools(),
            "graph": self.get_workflow_graph(workflow_id)
        }
