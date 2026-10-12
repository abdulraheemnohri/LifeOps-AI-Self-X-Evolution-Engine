import os
import subprocess
from typing import Dict, Any, Callable, Optional
from lifeops.security.policy import PolicyEngine, PolicyDecision, ApprovalGate

class ToolRegistry:
    def __init__(self, policy_engine: PolicyEngine, approval_gate: Optional[ApprovalGate] = None):
        self.policy_engine = policy_engine
        self.approval_gate = approval_gate
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register_tool(self, name: str, category: str, action_key: str, handler: Callable[..., Any], description: str):
        self.tools[name] = {
            "name": name,
            "category": category,
            "action_key": action_key,
            "handler": handler,
            "description": description
        }

    def _register_default_tools(self):
        # Filesystem read
        def fs_read(filepath: str):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

        # Filesystem write
        def fs_write(filepath: str, content: str):
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {filepath}"

        # Terminal execute
        def term_exec(command: str):
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            return {"stdout": res.stdout, "stderr": res.stderr, "exit_code": res.returncode}

        self.register_tool("filesystem.read_file", "filesystem", "filesystem.read", fs_read, "Read contents of a file")
        self.register_tool("filesystem.write_file", "filesystem", "filesystem.write", fs_write, "Write text content to a file")
        self.register_tool("terminal.execute", "terminal", "terminal.execute", term_exec, "Execute a shell command")

    def execute_tool(self, tool_name: str, kwargs: Dict[str, Any], agent_run_id: str, db=None) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {"status": "error", "message": f"Tool '{tool_name}' not found"}

        tool_info = self.tools[tool_name]
        action_key = tool_info["action_key"]
        decision = self.policy_engine.evaluate(action_key)

        if decision == PolicyDecision.BLOCK:
            return {"status": "blocked", "message": f"Action '{action_key}' is blocked by security policy."}

        if decision == PolicyDecision.ASK:
            if self.approval_gate and db:
                appr_id = self.approval_gate.request_approval(
                    agent_run_id=agent_run_id,
                    action_type=action_key,
                    description=f"Tool call '{tool_name}' with args {kwargs}",
                    payload={"tool_name": tool_name, "kwargs": kwargs}
                )
                return {"status": "awaiting_approval", "approval_id": appr_id, "message": "Action requires approval."}

        try:
            res = tool_info["handler"](**kwargs)
            return {"status": "success", "result": res}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
