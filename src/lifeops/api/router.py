import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from lifeops.storage.database import get_session_factory, get_engine, init_db
from lifeops.storage.models import User, Task, Note, Approval, Memory, Skill, AgentRun, TaskStatus, ApprovalDecision
from lifeops.lifeops.tasks import TaskService, NotificationService
from lifeops.security.policy import PolicyEngine, ApprovalGate
from lifeops.selfx.engine import SelfIdentity, SelfDiagnostics, SelfSkills, SelfMemory

app = FastAPI(title="LifeOps AI + Self-X API", version="0.1.0")

# WebSocket active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

def get_db():
    engine = get_engine()
    session_factory = get_session_factory(engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

# Health & System
@app.get("/api/v1/system/health")
def health_check(db: Session = Depends(get_db)):
    diag = SelfDiagnostics(db)
    return diag.run_health_check()

@app.get("/api/v1/system/identity")
def get_identity():
    return SelfIdentity.get_system_identity()

# Tasks API
@app.get("/api/v1/tasks")
def list_tasks(db: Session = Depends(get_db)):
    svc = TaskService(db)
    tasks = svc.list_tasks()
    return [{"id": t.id, "title": t.title, "priority": t.priority, "status": t.status.value} for t in tasks]

@app.post("/api/v1/tasks")
def create_task(payload: Dict[str, Any], db: Session = Depends(get_db)):
    svc = TaskService(db)
    task = svc.create_task(
        title=payload.get("title", "Untitled Task"),
        description=payload.get("description"),
        priority=payload.get("priority", "medium")
    )
    return {"id": task.id, "title": task.title, "status": task.status.value}

# Approvals API
@app.get("/api/v1/approvals")
def list_approvals(db: Session = Depends(get_db)):
    approvals = db.query(Approval).filter_by(decision=ApprovalDecision.PENDING).all()
    return [{"id": a.id, "action_type": a.action_type, "description": a.description, "payload": a.payload} for a in approvals]

@app.post("/api/v1/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    gate = ApprovalGate(db)
    decision_str = payload.get("decision", "APPROVED").upper()
    decision = ApprovalDecision.APPROVED if decision_str == "APPROVED" else ApprovalDecision.REJECTED
    success = gate.decide(approval_id, decision, payload.get("decided_by", "user"))
    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return {"status": "success", "approval_id": approval_id, "decision": decision.value}

# Real-time WebSocket
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
