import enum
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from src.lifeops.storage.models import Approval, ApprovalDecision, AuditEvent

class PolicyDecision(str, enum.Enum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    BLOCK = "BLOCK"

DEFAULT_POLICIES = {
    "filesystem.read": PolicyDecision.ALLOW,
    "filesystem.write": PolicyDecision.ASK,
    "filesystem.delete": PolicyDecision.ASK,
    "terminal.execute": PolicyDecision.ASK,
    "browser.navigate": PolicyDecision.ALLOW,
    "browser.interact": PolicyDecision.ASK,
    "network.outbound": PolicyDecision.ASK,
    "system.modify": PolicyDecision.BLOCK,
}

class PolicyEngine:
    def __init__(self, custom_policies: Optional[Dict[str, PolicyDecision]] = None):
        self.policies = dict(DEFAULT_POLICIES)
        if custom_policies:
            self.policies.update(custom_policies)

    def evaluate(self, action: str, context: Optional[Dict[str, Any]] = None) -> PolicyDecision:
        return self.policies.get(action, PolicyDecision.ASK)

class ApprovalGate:
    def __init__(self, db: DBSession):
        self.db = db

    def request_approval(self, agent_run_id: str, action_type: str, description: str, payload: Dict[str, Any]) -> str:
        import uuid
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        approval = Approval(
            id=approval_id,
            agent_run_id=agent_run_id,
            action_type=action_type,
            description=description,
            payload=payload,
            decision=ApprovalDecision.PENDING,
        )
        self.db.add(approval)
        self.db.commit()
        return approval_id

    def decide(self, approval_id: str, decision: ApprovalDecision, decided_by: str) -> bool:
        approval = self.db.query(Approval).filter_by(id=approval_id).first()
        if not approval:
            return False
        approval.decision = decision
        approval.decided_by = decided_by
        approval.decided_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.db.commit()
        return True

def log_audit_event(db: DBSession, actor: str, action: str, target: Optional[str], outcome: str, details: Optional[Dict[str, Any]] = None):
    # Redact secrets if present in details
    sanitized_details = None
    if details:
        sanitized_details = {}
        for k, v in details.items():
            if any(secret_key in k.lower() for secret_key in ["password", "token", "secret", "key"]):
                sanitized_details[k] = "[REDACTED]"
            else:
                sanitized_details[k] = v

    audit = AuditEvent(
        actor=actor,
        action=action,
        target=target,
        outcome=outcome,
        details=sanitized_details,
    )
    db.add(audit)
    db.commit()
