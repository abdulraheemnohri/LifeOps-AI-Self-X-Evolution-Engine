"""Independent, deterministic action policy. Model output is never authorization."""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass

class Decision(str, Enum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    BLOCK = "BLOCK"

@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str

# Hard blocks cannot be overridden by autonomy presets or approvals.
BLOCKED_ACTIONS = {"disable_authentication", "weaken_sandbox", "grant_self_permissions", "expose_secrets"}
APPROVAL_ACTIONS = {
    "delete_file", "move_file", "external_message", "publish_content",
    "execute_terminal", "install_dependency", "change_security_setting",
    "restore_backup", "apply_repair",
}
LOW_RISK_ACTIONS = {"read_note", "search_memory", "create_task", "create_note", "list_files"}

def decide(action: str, *, autonomy: str = "assist", preauthorized: set[str] | None = None) -> PolicyResult:
    action = action.strip().lower()
    if not action:
        return PolicyResult(Decision.BLOCK, "Action identifier is required.")
    if action in BLOCKED_ACTIONS:
        return PolicyResult(Decision.BLOCK, "This action is prohibited by a hard security rule.")
    if autonomy not in {"assist", "supervised", "bounded"}:
        return PolicyResult(Decision.BLOCK, "Unknown autonomy profile.")
    if action in APPROVAL_ACTIONS:
        return PolicyResult(Decision.ASK, "Sensitive action requires explicit human approval.")
    if action in LOW_RISK_ACTIONS and autonomy in {"supervised", "bounded"}:
        return PolicyResult(Decision.ALLOW, "Low-risk action is permitted by the selected profile.")
    if preauthorized and action in preauthorized and autonomy == "bounded":
        return PolicyResult(Decision.ALLOW, "Action is within the bounded pre-authorization list.")
    return PolicyResult(Decision.ASK, "Action is not explicitly permitted by current policy.")
