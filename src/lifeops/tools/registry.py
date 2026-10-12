"""Policy-enforced tool registry with a workspace boundary and safe subprocess defaults.

No handler runs when policy says ASK unless an approval gate is present and has
actually returned an executable approval. Terminal commands are argv arrays;
shell interpolation is deliberately unsupported.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from lifeops.security.policy import PolicyEngine, PolicyDecision, ApprovalGate


class ToolRegistry:
    def __init__(self, policy_engine: PolicyEngine, approval_gate: Optional[ApprovalGate] = None,
                 workspace: str | Path | None = None):
        self.policy_engine = policy_engine
        self.approval_gate = approval_gate
        self.workspace = Path(workspace or os.getenv("LIFEOPS_WORKSPACE_DIR", "workspace")).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register_tool(self, name: str, category: str, action_key: str,
                      handler: Callable[..., Any], description: str):
        self.tools[name] = {"name": name, "category": category, "action_key": action_key,
                            "handler": handler, "description": description}

    def _workspace_path(self, filepath: str) -> Path:
        candidate = Path(filepath).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("File access is restricted to the configured workspace.") from exc
        return resolved

    def _register_default_tools(self):
        def fs_read(filepath: str):
            path = self._workspace_path(filepath)
            if not path.is_file():
                raise FileNotFoundError("Workspace file does not exist.")
            if path.stat().st_size > 2_000_000:
                raise ValueError("Files larger than 2 MB cannot be read by this tool.")
            return path.read_text(encoding="utf-8")

        def fs_write(filepath: str, content: str):
            path = self._workspace_path(filepath)
            if not isinstance(content, str) or len(content.encode("utf-8")) > 2_000_000:
                raise ValueError("Content must be UTF-8 text no larger than 2 MB.")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"path": str(path.relative_to(self.workspace)), "bytes": len(content.encode("utf-8"))}

        def term_exec(argv: list[str]):
            if not isinstance(argv, list) or not argv or len(argv) > 64:
                raise ValueError("command must be a non-empty argv list of at most 64 items.")
            if any(not isinstance(part, str) or not part or len(part) > 4096 for part in argv):
                raise ValueError("Every argv item must be non-empty text of at most 4,096 characters.")
            if any("\x00" in part for part in argv):
                raise ValueError("NUL bytes are not allowed in argv.")
            # Never invoke a shell. This tool is policy-gated and runs in the workspace.
            result = subprocess.run(argv, shell=False, cwd=self.workspace, capture_output=True,
                                    text=True, timeout=10, check=False)
            return {"stdout": result.stdout[:20000], "stderr": result.stderr[:20000],
                    "exit_code": result.returncode}

        self.register_tool("filesystem.read_file", "filesystem", "filesystem.read", fs_read,
                           "Read a UTF-8 file from the workspace")
        self.register_tool("filesystem.write_file", "filesystem", "filesystem.write", fs_write,
                           "Write a UTF-8 file inside the workspace")
        self.register_tool("terminal.execute", "terminal", "terminal.execute", term_exec,
                           "Run an argv command without a shell; requires policy approval")

    def execute_tool(self, tool_name: str, kwargs: Dict[str, Any], agent_run_id: str, db=None) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {"status": "error", "message": f"Tool '{tool_name}' not found"}
        tool_info = self.tools[tool_name]
        decision = self.policy_engine.evaluate(tool_info["action_key"])
        if decision == PolicyDecision.BLOCK:
            return {"status": "blocked", "message": "Action is blocked by security policy."}
        if decision == PolicyDecision.ASK:
            if self.approval_gate is None or db is None:
                return {"status": "awaiting_approval", "message": "No approval service is available; action was not executed."}
            approval_id = self.approval_gate.request_approval(
                agent_run_id=agent_run_id, action_type=tool_info["action_key"],
                description=f"Tool call '{tool_name}' requires review.",
                payload={"tool_name": tool_name, "kwargs": kwargs},
            )
            return {"status": "awaiting_approval", "approval_id": approval_id,
                    "message": "Action queued for explicit approval; it was not executed."}
        try:
            result = tool_info["handler"](**kwargs)
            return {"status": "success", "result": result}
        except Exception as exc:
            return {"status": "failed", "error": f"{type(exc).__name__}: {str(exc)[:1000]}"}
