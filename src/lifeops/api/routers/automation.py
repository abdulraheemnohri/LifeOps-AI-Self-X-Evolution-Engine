"""Automation routers: workflows, scheduler jobs, worker queue."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from lifeops.api.deps import get_db, require_not_stopped
from lifeops.api.helpers import paged, raise_lookup, raise_value
from lifeops.scheduler.worker import JOB_HANDLERS, CronExpression
from lifeops.security.policy import log_audit_event
from lifeops.services import crud
from lifeops.storage.models import JobEvent, ScheduledJob
from lifeops.workflows.engine import WorkflowDefinition, WorkflowRun, validate_definition

router = APIRouter(prefix="/api/v1", tags=["automation"], dependencies=[Depends(require_not_stopped)])


def _engine(db: DBSession, request: Request):
    from lifeops.workflows.engine import WorkflowEngine
    registry = getattr(request.app.state, "tool_registry", None)
    return WorkflowEngine(db, tool_registry=registry)


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------

@router.get("/workflows")
def list_workflows(status: Optional[str] = None, db: DBSession = Depends(get_db)):
    q = db.query(WorkflowDefinition)
    if status:
        q = q.filter(WorkflowDefinition.status == status)
    rows = q.order_by(WorkflowDefinition.updated_at.desc()).all()
    return [crud.to_dict(w) for w in rows]


@router.post("/workflows")
def create_workflow(payload: dict, db: DBSession = Depends(get_db)):
    name = payload.get("name", "").strip()
    definition = payload.get("definition") or {}
    if not name:
        raise HTTPException(status_code=422, detail="'name' is required")
    if "steps" not in definition:
        definition = {**definition, "name": name}
    ok, errors = validate_definition(definition)
    if not ok:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    wf = _make_engine(db).create_workflow(name=name, definition=definition)
    return crud.to_dict(wf)


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str, db: DBSession = Depends(get_db)):
    try:
        wf = crud.get_or_404(db, WorkflowDefinition, workflow_id)
    except LookupError as exc:
        raise_lookup(exc)
    data = crud.to_dict(wf)
    ok, errors = validate_definition(wf.definition)
    data["validation"] = {"valid": ok, "errors": errors}
    return data


@router.put("/workflows/{workflow_id}/definition")
def edit_workflow(workflow_id: str, payload: dict, request: Request, db: DBSession = Depends(get_db)):
    definition = payload.get("definition")
    if not isinstance(definition, dict):
        raise HTTPException(status_code=422, detail="'definition' object is required")
    try:
        wf = _engine(db, request).new_version(workflow_id, definition)
    except LookupError as exc:
        raise_lookup(exc)
    except ValueError as exc:
        raise_value(exc)
    return crud.to_dict(wf)


@router.post("/workflows/{workflow_id}/activate")
def activate_workflow(workflow_id: str, db: DBSession = Depends(get_db)):
    try:
        wf = _make_engine(db).activate(workflow_id)
    except LookupError as exc:
        raise_lookup(exc)
    except ValueError as exc:
        raise_value(exc)
    log_audit_event(db, actor="user", action="workflow.activate", target=workflow_id, outcome="success")
    return crud.to_dict(wf)


def _make_engine(db):
    from lifeops.workflows.engine import WorkflowEngine
    return WorkflowEngine(db)


@router.post("/workflows/{workflow_id}/{action}")
def workflow_lifecycle(workflow_id: str, action: str, db: DBSession = Depends(get_db)):
    mapping = {"pause": "paused", "resume": "active", "disable": "disabled"}
    if action not in mapping:
        raise HTTPException(status_code=422, detail=f"unknown action '{action}'")
    try:
        wf = _make_engine(db).set_status(workflow_id, mapping[action])
    except LookupError as exc:
        raise_lookup(exc)
    except ValueError as exc:
        raise_value(exc)
    return crud.to_dict(wf)


@router.post("/workflows/{workflow_id}/duplicate")
def duplicate_workflow(workflow_id: str, db: DBSession = Depends(get_db)):
    try:
        wf = _make_engine(db).duplicate(workflow_id)
    except LookupError as exc:
        raise_lookup(exc)
    return crud.to_dict(wf)


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str, db: DBSession = Depends(get_db)):
    wf = crud.get_or_404(db, WorkflowDefinition, workflow_id)
    crud.delete_object(db, wf, action="workflow.delete")
    return {"status": "deleted", "id": workflow_id}


@router.get("/workflows/{workflow_id}/plan")
def preview_plan(workflow_id: str, db: DBSession = Depends(get_db)):
    try:
        return _make_engine(db).preview_plan(workflow_id)
    except LookupError as exc:
        raise_lookup(exc)


@router.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str, payload: dict = None, request: Request = None,
                 db: DBSession = Depends(get_db)):
    payload = payload or {}
    test_run = bool(payload.get("test_run", False))
    sample_data = payload.get("sample_data") or {}
    try:
        run = _engine(db, request).run(workflow_id, sample_data=sample_data, test_run=test_run)
    except LookupError as exc:
        raise_lookup(exc)
    except ValueError as exc:
        raise_value(exc)
    return crud.to_dict(run)


@router.get("/workflows/{workflow_id}/runs")
def workflow_runs(workflow_id: str, db: DBSession = Depends(get_db)):
    runs = _make_engine(db).runs_for(workflow_id)
    return [crud.to_dict(r) for r in runs]


@router.get("/workflows/runs/{run_id}")
def get_workflow_run(run_id: str, db: DBSession = Depends(get_db)):
    try:
        return crud.to_dict(crud.get_or_404(db, WorkflowRun, run_id))
    except LookupError as exc:
        raise_lookup(exc)


# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------

@router.get("/scheduler/jobs")
def list_jobs(db: DBSession = Depends(get_db)):
    rows = db.query(ScheduledJob).order_by(ScheduledJob.name).all()
    return [crud.to_dict(j) for j in rows]


@router.post("/scheduler/jobs")
def create_job(payload: dict, db: DBSession = Depends(get_db)):
    name = payload.get("name", "").strip()
    cron = payload.get("cron_expression", "")
    action = payload.get("action") or {}
    if not name:
        raise HTTPException(status_code=422, detail="'name' is required")
    if not isinstance(action, dict) or "handler" not in action:
        raise HTTPException(status_code=422, detail="'action.handler' is required")
    if action["handler"] not in JOB_HANDLERS:
        raise HTTPException(status_code=422,
                            detail=f"unknown handler '{action['handler']}'. Available: "
                                   f"{sorted(JOB_HANDLERS)}")
    if cron:
        try:
            CronExpression(cron)
        except ValueError as exc:
            raise_value(ValueError(str(exc)))
    job = ScheduledJob(id=f"job_{uuid.uuid4().hex[:12]}", name=name,
                       cron_expression=cron, action=action,
                       enabled=bool(payload.get("enabled", True)))
    db.add(job); db.commit(); db.refresh(job)
    log_audit_event(db, actor="user", action="scheduler.job.create", target=job.id, outcome="success")
    return crud.to_dict(job)


@router.patch("/scheduler/jobs/{job_id}")
def update_job(job_id: str, payload: dict, db: DBSession = Depends(get_db)):
    job = crud.get_or_404(db, ScheduledJob, job_id)
    data = {k: v for k, v in payload.items() if k in ("name", "action", "enabled")}
    if "cron_expression" in payload:
        try:
            CronExpression(payload["cron_expression"])
        except ValueError as exc:
            raise_value(ValueError(str(exc)))
        data["cron_expression"] = payload["cron_expression"]
    return crud.to_dict(crud.apply_update(db, job, data, action="scheduler.job.update"))


@router.delete("/scheduler/jobs/{job_id}")
def delete_job(job_id: str, db: DBSession = Depends(get_db)):
    job = crud.get_or_404(db, ScheduledJob, job_id)
    crud.delete_object(db, job, action="scheduler.job.delete")
    return {"status": "deleted", "id": job_id}


@router.post("/scheduler/jobs/{job_id}/run-now")
def run_job_now(job_id: str, request: Request, db: DBSession = Depends(get_db)):
    try:
        crud.get_or_404(db, ScheduledJob, job_id)
    except LookupError as exc:
        raise_lookup(exc)
    queue = getattr(request.app.state, "worker_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="worker queue not available")
    accepted = queue.enqueue(job_id)
    return {"job_id": job_id, "queued": accepted}


@router.get("/scheduler/jobs/{job_id}/events")
def job_events(job_id: str, limit: int = 100, db: DBSession = Depends(get_db)):
    rows = (db.query(JobEvent).filter_by(job_id=job_id)
            .order_by(JobEvent.timestamp.desc()).limit(min(limit, 500)).all())
    return {"job_id": job_id, "events": [crud.to_dict(e) for e in rows]}


# ---------------------------------------------------------------------------
# Worker queue stats
# ---------------------------------------------------------------------------

@router.get("/workers/stats")
def worker_stats(request: Request):
    queue = getattr(request.app.state, "worker_queue", None)
    if queue is None:
        return {"available": False}
    stats = queue.stats()
    stats["available"] = True
    return stats
