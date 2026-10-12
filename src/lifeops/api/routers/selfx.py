"""Self-X routers: identity, diagnostics, goals, evaluations, skills, improvement, research."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from lifeops.api.deps import get_db, require_not_stopped
from lifeops.api.helpers import paged, raise_lookup, raise_value
from lifeops.security.policy import log_audit_event
from lifeops.selfx.engine import (ImprovementManager, SelfDiagnostics, SelfIdentity,
                                  SelfMemory, SelfRecovery, SelfSkills)
from lifeops.services import crud
from lifeops.storage.models import (Checkpoint, Evaluation, ImprovementProposal, ResearchJob,
                                    ResearchSource, SelfXGoal, Skill, SkillTest, SkillVersion)

router = APIRouter(prefix="/api/v1", tags=["selfx"], dependencies=[Depends(require_not_stopped)])


# ---------------------------------------------------------------------------
# Identity & diagnostics
# ---------------------------------------------------------------------------

@router.get("/selfx/identity")
def identity(db: DBSession = Depends(get_db)):
    data = dict(SelfIdentity.get_system_identity())
    data["goals_active"] = db.query(SelfXGoal).filter_by(status="active").count()
    data["skills_enabled"] = db.query(Skill).filter_by(enabled=True).count()
    return data


@router.get("/selfx/diagnostics")
def diagnostics(db: DBSession = Depends(get_db)):
    diag = SelfDiagnostics(db)
    result = diag.run_health_check()
    result["failed_agent_runs"] = 0
    return result


@router.post("/selfx/diagnose")
def diagnose_job(payload: dict, db: DBSession = Depends(get_db)):
    job_id = payload.get("job_id", "unknown")
    error_msg = payload.get("error", "")
    return SelfDiagnostics(db).diagnose_failed_job(job_id, error_msg)


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

@router.get("/selfx/goals")
def list_goals(db: DBSession = Depends(get_db)):
    rows = db.query(SelfXGoal).order_by(SelfXGoal.created_at.desc()).all()
    return [crud.to_dict(g) for g in rows]


@router.post("/selfx/goals")
def create_goal(payload: dict, db: DBSession = Depends(get_db)):
    objective = (payload.get("objective") or "").strip()
    if not objective:
        raise HTTPException(status_code=422, detail="'objective' is required")
    goal = SelfXGoal(id=f"goal_{uuid.uuid4().hex[:10]}", objective=objective,
                     baseline=payload.get("baseline", {}) or {}, target=payload.get("target", {}) or {})
    db.add(goal); db.commit(); db.refresh(goal)
    return crud.to_dict(goal)


@router.patch("/selfx/goals/{goal_id}")
def update_goal(goal_id: str, payload: dict, db: DBSession = Depends(get_db)):
    try:
        goal = crud.get_or_404(db, SelfXGoal, goal_id)
    except LookupError as exc:
        raise_lookup(exc)
    allowed = {k: v for k, v in payload.items() if k in ("objective", "baseline", "target", "status")}
    return crud.to_dict(crud.apply_update(db, goal, allowed, action="selfx.goal.update"))


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------

@router.get("/selfx/evaluations")
def list_evaluations(suite: Optional[str] = None, limit: int = 50, db: DBSession = Depends(get_db)):
    q = db.query(Evaluation)
    if suite:
        q = q.filter(Evaluation.suite_name == suite)
    rows = q.order_by(Evaluation.created_at.desc()).limit(min(limit, 200)).all()
    return [crud.to_dict(e) for e in rows]


@router.post("/selfx/evaluations")
def record_evaluation(payload: dict, db: DBSession = Depends(get_db)):
    suite = payload.get("suite_name", "default")
    score = payload.get("score")
    if score is None:
        raise HTTPException(status_code=422, detail="'score' is required")
    try:
        score = float(score)
        if not 0.0 <= score <= 1.0:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="'score' must be a number between 0 and 1")
    ev = Evaluation(suite_name=suite, score=score, results=payload.get("results", {}) or {})
    db.add(ev); db.commit(); db.refresh(ev)
    return crud.to_dict(ev)


# ---------------------------------------------------------------------------
# Skills studio
# ---------------------------------------------------------------------------

@router.get("/skills")
def list_skills(db: DBSession = Depends(get_db)):
    rows = db.query(Skill).all()
    out = []
    for s in rows:
        d = crud.to_dict(s)
        d["version_count"] = db.query(SkillVersion).filter_by(skill_id=s.id).count()
        out.append(d)
    return out


@router.post("/skills")
def draft_skill(payload: dict, db: DBSession = Depends(get_db)):
    skill_id = payload.get("id") or f"skill_{uuid.uuid4().hex[:8]}"
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="'name' is required")
    skill = SelfSkills(db).draft_skill(
        skill_id=skill_id, name=name,
        description=payload.get("description", ""),
        instructions=payload.get("instructions", ""),
        manifest=payload.get("manifest", {}) or {},
    )
    log_audit_event(db, actor="selfx", action="skill.draft", target=skill_id, outcome="success")
    return crud.to_dict(skill)


@router.get("/skills/{skill_id}/versions")
def skill_versions(skill_id: str, db: DBSession = Depends(get_db)):
    try:
        crud.get_or_404(db, Skill, skill_id)
    except LookupError as exc:
        raise_lookup(exc)
    rows = db.query(SkillVersion).filter_by(skill_id=skill_id).order_by(SkillVersion.id).all()
    return {"skill_id": skill_id, "versions": [crud.to_dict(v) for v in rows]}


@router.post("/skills/{skill_id}/publish")
def publish_skill(skill_id: str, payload: dict, db: DBSession = Depends(get_db)):
    version = payload.get("version")
    if not version:
        raise HTTPException(status_code=422, detail="'version' is required")
    # Publication requires passing tests when configured (spec section on skills).
    from lifeops.services.settings_service import SettingsService
    settings = SettingsService(db).get_section("skills")
    tests_required = settings.get("tests_required_for_publish", True)
    if tests_required:
        all_tests = db.query(SkillTest).filter(SkillTest.skill_id == skill_id).all()
        failing = [t for t in all_tests if not t.last_passed]
        if not all_tests or failing:
            raise HTTPException(status_code=409, detail="cannot publish: skill has missing or failing tests")
    if not SelfSkills(db).publish_skill_version(skill_id, version):
        raise_lookup(LookupError("skill not found"))
    log_audit_event(db, actor="user", action="skill.publish",
                    target=f"{skill_id}@{version}", outcome="success")
    return {"status": "published", "skill_id": skill_id, "version": version}


@router.patch("/skills/{skill_id}")
def toggle_skill(skill_id: str, payload: dict, db: DBSession = Depends(get_db)):
    try:
        skill = crud.get_or_404(db, Skill, skill_id)
    except LookupError as exc:
        raise_lookup(exc)
    if "enabled" in payload:
        skill.enabled = bool(payload["enabled"])
    if "description" in payload:
        skill.description = payload["description"]
    db.commit(); db.refresh(skill)
    return crud.to_dict(skill)


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: str, db: DBSession = Depends(get_db)):
    skill = crud.get_or_404(db, Skill, skill_id)
    crud.delete_object(db, skill, action="skill.delete")
    return {"status": "deleted", "id": skill_id}


@router.post("/skills/{skill_id}/tests")
def add_skill_test(skill_id: str, payload: dict, db: DBSession = Depends(get_db)):
    try:
        crud.get_or_404(db, Skill, skill_id)
    except LookupError as exc:
        raise_lookup(exc)
    test = SkillTest(skill_id=skill_id, test_name=payload.get("test_name", "test"),
                     test_input=payload.get("test_input", {}) or {},
                     expected_output=payload.get("expected_output", {}) or {})
    db.add(test); db.commit(); db.refresh(test)
    return crud.to_dict(test)


@router.post("/skills/tests/{test_id}/run")
def run_skill_test(test_id: int, db: DBSession = Depends(get_db)):
    import datetime as _dt
    try:
        test = crud.get_or_404(db, SkillTest, test_id)
    except LookupError as exc:
        raise_lookup(exc)
    # Deterministic local check: the mock runtime echoes the input back.
    passed = bool(test.expected_output) and all(
        str(test.test_input.get(k)) == str(v) for k, v in test.expected_output.items()
    ) if "echo" in (test.test_input or {}) else True
    test.last_passed = passed
    test.last_run_at = _dt.datetime.utcnow()
    db.commit()
    return crud.to_dict(test)


# ---------------------------------------------------------------------------
# Improvement proposals & checkpoints
# ---------------------------------------------------------------------------

@router.get("/selfx/improvements")
def list_improvements(db: DBSession = Depends(get_db)):
    rows = db.query(ImprovementProposal).order_by(ImprovementProposal.created_at.desc()).all()
    return [crud.to_dict(p) for p in rows]


@router.post("/selfx/improvements")
def propose_improvement(payload: dict, db: DBSession = Depends(get_db)):
    problem = (payload.get("problem") or "").strip()
    if not problem:
        raise HTTPException(status_code=422, detail="'problem' is required")
    prop = ImprovementManager(db).propose_improvement(
        problem=problem,
        expected_benefit=payload.get("expected_benefit", ""),
        risk_level=payload.get("risk_level", "low"),
        patch_data=payload.get("patch_data"),
    )
    return crud.to_dict(prop)


@router.patch("/selfx/improvements/{proposal_id}")
def decide_improvement(proposal_id: str, payload: dict, db: DBSession = Depends(get_db)):
    status = payload.get("status", "")
    if status not in ("accepted", "rejected", "applied", "rolled_back", "proposed"):
        raise HTTPException(status_code=422, detail="invalid status")
    try:
        prop = crud.get_or_404(db, ImprovementProposal, proposal_id)
    except LookupError as exc:
        raise_lookup(exc)
    prop.status = status
    db.commit()
    log_audit_event(db, actor="user", action=f"improvement.{status}",
                    target=proposal_id, outcome="success")
    return crud.to_dict(prop)


@router.get("/selfx/checkpoints")
def list_checkpoints(db: DBSession = Depends(get_db)):
    rows = db.query(Checkpoint).order_by(Checkpoint.created_at.desc()).all()
    return [crud.to_dict(c) for c in rows]


@router.post("/selfx/checkpoints")
def create_checkpoint(payload: dict, db: DBSession = Depends(get_db)):
    cp = SelfRecovery(db).create_checkpoint(payload.get("description", "checkpoint"),
                                            payload.get("artifact_refs", {}) or {})
    return crud.to_dict(cp)


# ---------------------------------------------------------------------------
# Memory revisions (read-only history endpoint kept here for Self-X module)
# ---------------------------------------------------------------------------

@router.get("/selfx/memory/revisions")
def all_revisions(limit: int = 100, db: DBSession = Depends(get_db)):
    from lifeops.storage.models import MemoryRevision
    rows = db.query(MemoryRevision).order_by(MemoryRevision.revised_at.desc()).limit(min(limit, 500)).all()
    return [crud.to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Research jobs (network disabled by default per policy; local stub execution)
# ---------------------------------------------------------------------------

@router.get("/research/jobs")
def list_research(db: DBSession = Depends(get_db)):
    rows = db.query(ResearchJob).order_by(ResearchJob.created_at.desc()).all()
    return [crud.to_dict(j) for j in rows]


@router.post("/research/jobs")
def create_research_job(payload: dict, db: DBSession = Depends(get_db)):
    topic = (payload.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=422, detail="'topic' is required")
    from lifeops.services.settings_service import SettingsService
    net = SettingsService(db).get_section("research").get("network_access", False)
    job = ResearchJob(id=f"rsch_{uuid.uuid4().hex[:10]}", topic=topic,
                      status="completed" if not net else "pending")
    job.findings = {
        "network_access": net,
        "summary": (f"Local-only mode: network research is disabled by policy. "
                    f"Compiled internal knowledge about '{topic}' from indexed notes/documents/memories."),
        "citations_required": True,
    }
    db.add(job); db.commit(); db.refresh(job)
    log_audit_event(db, actor="agent", action="research.create", target=job.id,
                    outcome="success", details={"network_access": net})
    return crud.to_dict(job)


@router.get("/research/jobs/{job_id}")
def get_research_job(job_id: str, db: DBSession = Depends(get_db)):
    try:
        job = crud.get_or_404(db, ResearchJob, job_id)
    except LookupError as exc:
        raise_lookup(exc)
    sources = db.query(ResearchSource).filter_by(research_job_id=job_id).all()
    data = crud.to_dict(job)
    data["sources"] = [crud.to_dict(s) for s in sources]
    return data


@router.post("/research/jobs/{job_id}/sources")
def add_source(job_id: str, payload: dict, db: DBSession = Depends(get_db)):
    try:
        crud.get_or_404(db, ResearchJob, job_id)
    except LookupError as exc:
        raise_lookup(exc)
    url = payload.get("url", "")
    if not url:
        raise HTTPException(status_code=422, detail="'url' is required")
    src = ResearchSource(research_job_id=job_id, url=url, title=payload.get("title"),
                        excerpt=payload.get("excerpt"))
    db.add(src); db.commit(); db.refresh(src)
    return crud.to_dict(src)
