"""Validated business services shared by browser routes and background workers."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from lifeops.database import Task, Note, Memory, Project, Approval, AgentRun, SelfGoal, Evaluation, ImprovementProposal, AuditEvent
VALID_PRIORITIES = {"low", "medium", "high"}
class ValidationError(ValueError): pass

def _audit(db: Session, event_type: str, details: str) -> None:
    db.add(AuditEvent(event_type=event_type, details=details[:1000]))

def create_task(db: Session, title: str, description: str = "", priority: str = "medium", project_id: int | None = None) -> Task:
    title = title.strip()
    if not title or len(title) > 240: raise ValidationError("Task title must contain 1–240 characters.")
    if priority not in VALID_PRIORITIES: raise ValidationError("Priority must be low, medium, or high.")
    if project_id is not None and db.get(Project, project_id) is None: raise ValidationError("Project does not exist.")
    task = Task(title=title, description=description.strip()[:10000], priority=priority, project_id=project_id)
    db.add(task); _audit(db, "task.created", f"title={title}"); db.commit(); db.refresh(task)
    return task

def list_tasks(db: Session, status: str | None = None) -> list[Task]:
    stmt = select(Task).order_by(Task.created_at.desc(), Task.id.desc())
    if status in {"open", "completed"}: stmt = stmt.where(Task.status == status)
    return list(db.scalars(stmt).all())

def update_task(db: Session, task_id: int, *, title: str | None = None, description: str | None = None, priority: str | None = None, project_id: int | None = None) -> Task:
    task = db.get(Task, task_id)
    if task is None: raise LookupError("Task not found.")
    if title is not None:
        title = title.strip()
        if not title or len(title) > 240: raise ValidationError("Task title must contain 1–240 characters.")
        task.title = title
    if description is not None: task.description = description.strip()[:10000]
    if priority is not None:
        if priority not in VALID_PRIORITIES: raise ValidationError("Priority must be low, medium, or high.")
        task.priority = priority
    if project_id is not None:
        if db.get(Project, project_id) is None: raise ValidationError("Project does not exist.")
        task.project_id = project_id
    _audit(db, "task.updated", f"task_id={task.id}"); db.commit(); db.refresh(task); return task

def delete_task(db: Session, task_id: int) -> None:
    task = db.get(Task, task_id)
    if task is None: raise LookupError("Task not found.")
    _audit(db, "task.deleted", f"task_id={task.id}"); db.delete(task); db.commit()

def complete_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None: raise LookupError("Task not found.")
    task.status = "completed"; task.completed_at = datetime.now(timezone.utc)
    _audit(db, "task.completed", f"task_id={task.id}"); db.commit(); db.refresh(task)
    return task

def create_project(db: Session, name: str, description: str = "") -> Project:
    name = name.strip()
    if not name or len(name) > 160: raise ValidationError("Project name must contain 1–160 characters.")
    if db.scalar(select(Project).where(Project.name == name)): raise ValidationError("Project name already exists.")
    project = Project(name=name, description=description.strip()[:5000])
    db.add(project); _audit(db, "project.created", f"name={name}"); db.commit(); db.refresh(project); return project

def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.name)).all())

def create_note(db: Session, title: str, content: str = "") -> Note:
    title = title.strip()
    if not title or len(title) > 240: raise ValidationError("Note title must contain 1–240 characters.")
    if len(content) > 100000: raise ValidationError("Note content exceeds 100,000 characters.")
    note = Note(title=title, content=content); db.add(note); _audit(db, "note.created", f"title={title}")
    db.commit(); db.refresh(note); return note

def list_notes(db: Session, query: str = "") -> list[Note]:
    stmt = select(Note).order_by(Note.updated_at.desc(), Note.id.desc())
    query = query.strip()[:200]
    if query: stmt = stmt.where(or_(Note.title.ilike(f"%{query}%"), Note.content.ilike(f"%{query}%")))
    return list(db.scalars(stmt).all())

def update_note(db: Session, note_id: int, *, title: str, content: str) -> Note:
    note = db.get(Note, note_id)
    if note is None: raise LookupError("Note not found.")
    title = title.strip()
    if not title or len(title) > 240: raise ValidationError("Note title must contain 1–240 characters.")
    if len(content) > 100000: raise ValidationError("Note content exceeds 100,000 characters.")
    note.title, note.content = title, content
    _audit(db, "note.updated", f"note_id={note.id}"); db.commit(); db.refresh(note); return note

def delete_note(db: Session, note_id: int) -> None:
    note = db.get(Note, note_id)
    if note is None: raise LookupError("Note not found.")
    _audit(db, "note.deleted", f"note_id={note_id}"); db.delete(note); db.commit()

def create_memory(db: Session, content: str, category: str = "general", source: str = "user", confidence: float = 1.0) -> Memory:
    content = content.strip(); category = category.strip().lower()
    if not content or len(content) > 10000: raise ValidationError("Memory must contain 1–10,000 characters.")
    if category not in {"general", "preference", "project", "procedure", "lesson", "research"}: raise ValidationError("Unsupported memory category.")
    if not 0.0 <= confidence <= 1.0: raise ValidationError("Confidence must be between 0 and 1.")
    memory = Memory(content=content, category=category, source=source[:240], confidence=confidence)
    db.add(memory); _audit(db, "memory.created", f"category={category}"); db.commit(); db.refresh(memory); return memory

def search_memories(db: Session, query: str = "") -> list[Memory]:
    stmt = select(Memory).order_by(Memory.updated_at.desc(), Memory.id.desc())
    query = query.strip()[:200]
    if query: stmt = stmt.where(Memory.content.ilike(f"%{query}%"))
    return list(db.scalars(stmt).all())

def delete_memory(db: Session, memory_id: int) -> None:
    memory = db.get(Memory, memory_id)
    if memory is None: raise LookupError("Memory not found.")
    _audit(db, "memory.deleted", f"memory_id={memory_id}"); db.delete(memory); db.commit()

def create_approval(db: Session, action: str, summary: str, risk: str = "high") -> Approval:
    if risk not in {"low", "medium", "high", "critical"}: raise ValidationError("Invalid risk level.")
    if not action.strip() or len(summary.strip()) < 1: raise ValidationError("Action and summary are required.")
    item = Approval(action=action.strip()[:120], summary=summary.strip()[:5000], risk=risk)
    db.add(item); _audit(db, "approval.created", f"action={item.action};risk={risk}"); db.commit(); db.refresh(item); return item

def decide_approval(db: Session, approval_id: int, *, approve: bool, actor: str, reason: str = "") -> Approval:
    item = db.get(Approval, approval_id)
    if item is None: raise LookupError("Approval not found.")
    if item.status != "pending": raise ValidationError("Approval has already been decided.")
    item.status = "approved" if approve else "rejected"
    item.decided_by = actor.strip()[:120] or "local-user"; item.decision_reason = reason.strip()[:2000]
    item.decided_at = datetime.now(timezone.utc)
    _audit(db, f"approval.{item.status}", f"approval_id={item.id};actor={item.decided_by}")
    db.commit(); db.refresh(item); return item

def list_approvals(db: Session, status: str | None = "pending") -> list[Approval]:
    stmt = select(Approval).order_by(Approval.created_at.desc(), Approval.id.desc())
    if status in {"pending", "approved", "rejected"}: stmt = stmt.where(Approval.status == status)
    return list(db.scalars(stmt).all())

def create_agent_run(db: Session, request: str) -> AgentRun:
    request = request.strip()
    if not request or len(request) > 20000: raise ValidationError("Run request must contain 1–20,000 characters.")
    run = AgentRun(request=request, status="needs_input", error="Model runtime is not configured; no actions were executed.")
    db.add(run); _audit(db, "agent_run.created", "stored request; execution unavailable without model adapter")
    db.commit(); db.refresh(run); return run

def create_self_goal(db: Session, title: str, objective: str, baseline: str, target: str) -> SelfGoal:
    title, objective = title.strip(), objective.strip()
    if not title or len(title) > 240 or not objective or len(objective) > 5000:
        raise ValidationError("Goal title and objective are required and must fit their limits.")
    if len(baseline) > 5000 or len(target) > 5000: raise ValidationError("Baseline and target must be at most 5,000 characters.")
    goal = SelfGoal(title=title, objective=objective, baseline=baseline.strip(), target=target.strip())
    db.add(goal); _audit(db, "selfx.goal.created", f"title={title}"); db.commit(); db.refresh(goal); return goal

def create_evaluation_record(db: Session, name: str, suite_version: str, *, score: float | None, details: str = "") -> Evaluation:
    name, suite_version = name.strip(), suite_version.strip()
    if not name or len(name) > 240 or not suite_version or len(suite_version) > 80:
        raise ValidationError("Evaluation name and suite version are required.")
    if score is not None and not 0.0 <= score <= 1.0: raise ValidationError("Score must be between 0 and 1.")
    if len(details) > 20000: raise ValidationError("Evaluation details exceed 20,000 characters.")
    record = Evaluation(name=name, suite_version=suite_version, score=score, details=details[:20000])
    db.add(record); _audit(db, "selfx.evaluation.recorded", f"name={name};score={score}"); db.commit(); db.refresh(record); return record

def create_improvement_proposal(db: Session, title: str, problem: str, evidence: str, expected_benefit: str, risk: str, rollback_plan: str) -> ImprovementProposal:
    title, problem, rollback_plan = title.strip(), problem.strip(), rollback_plan.strip()
    if not title or len(title) > 240 or not problem or not rollback_plan:
        raise ValidationError("Proposal title, problem, and rollback plan are required.")
    if risk not in {"low", "medium", "high", "critical"}: raise ValidationError("Invalid risk classification.")
    if any(len(v) > 10000 for v in (problem, evidence, expected_benefit, rollback_plan)):
        raise ValidationError("Proposal fields must be at most 10,000 characters.")
    proposal = ImprovementProposal(title=title, problem=problem, evidence=evidence, expected_benefit=expected_benefit, risk=risk, rollback_plan=rollback_plan)
    db.add(proposal); _audit(db, "selfx.improvement.proposed", f"title={title};risk={risk}"); db.commit(); db.refresh(proposal); return proposal

def decide_improvement_proposal(db: Session, proposal_id: int, *, approve: bool, reason: str = "") -> ImprovementProposal:
    proposal = db.get(ImprovementProposal, proposal_id)
    if proposal is None: raise LookupError("Improvement proposal not found.")
    if proposal.status != "proposed": raise ValidationError("Proposal has already been reviewed.")
    # Approval means permission to run a separately sandboxed trial, not automatic deployment.
    proposal.status = "approved_for_trial" if approve else "rejected"
    _audit(db, f"selfx.improvement.{proposal.status}", f"proposal_id={proposal.id};reason={reason[:500]}")
    db.commit(); db.refresh(proposal); return proposal
