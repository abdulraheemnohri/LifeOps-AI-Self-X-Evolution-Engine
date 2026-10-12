# LifeOps AI + Self-X Evolution Engine Documentation

## System Architecture

LifeOps AI + Self-X is a local-first, self-hosted personal productivity platform and agent framework.

### Architecture Subsystems
1. **Presentation Layer**: FastHTML + HTMX responsive Web UI (Dark theme).
2. **API & Real-time Layer**: FastAPI REST API and WebSocket events (`/ws/events`).
3. **Security & Policy**: PolicyEngine (ALLOW, ASK, BLOCK) and ApprovalGate for human-in-the-loop controls.
4. **Agent Orchestrator**: Planner, Executor, and Tool Registry.
5. **Self-X Subsystem**: Identity, Diagnostics, Research, Skills Studio, Memory Explorer, and Recovery Manager.
6. **Storage Layer**: SQLite 3.x using SQLAlchemy 2.x declarative models across 33 relational tables.

## Quickstart & Installation

### Linux
```bash
./scripts/install_linux.sh
./scripts/start_linux.sh
```

### Windows (PowerShell)
```powershell
.\scripts\install_windows.ps1
.\scripts\start_windows.ps1
```

### System Doctor / Verification
```bash
python3 scripts/doctor.py
```
