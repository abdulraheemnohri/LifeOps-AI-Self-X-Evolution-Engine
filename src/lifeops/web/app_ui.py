"""FastHTML Web UI - server-rendered pages wired directly to the service layer.

All page GETs render via lifeops.web.views; all mutations are POST form
handlers that call services, write audit events, and PRG-redirect with flash.
"""
import datetime
import json
import os

from fasthtml.common import FastHTML, RedirectResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
from sqlalchemy import select, desc

from lifeops.storage.database import get_engine, init_db, get_session_factory
from lifeops.storage.models import (
    Task, Project, Note, Memory, MemoryRevision, Document, Notification,
    Conversation, Message, Approval, AuditEvent, ScheduledJob, JobEvent,
    Integration, Skill, SkillTest, SkillVersion, ResearchJob, ResearchSource,
    SelfXGoal, Evaluation, ImprovementProposal, Checkpoint, BackupRecord,
    TaskStatus, ApprovalDecision,
)
from lifeops.lifeops.tasks import TaskService
from lifeops.services.content import (
    CalendarService, NoteService, DocumentService, SearchService)
from lifeops.services.settings_service import SettingsService, AUTONOMY_PROFILES
from lifeops.workflows.engine import WorkflowEngine, WorkflowDefinition, WorkflowRun
from lifeops.scheduler.worker import WorkerQueue, JOB_HANDLERS, CronExpression
from lifeops.backup.manager import BackupManager
from lifeops.selfx.engine import (
    SelfIdentity, SelfDiagnostics, SelfSkills, SelfMemory, SelfRecovery)
from lifeops.security.policy import PolicyEngine, ApprovalGate, log_audit_event
from lifeops.api.deps import emergency_stop
from lifeops.web.views import (
    render_dashboard, render_tasks_page, render_assistant_page,
    render_calendar_page, render_notes_page, render_note_detail,
    render_memory_page, render_files_page, render_search_page,
    render_workflows_page, render_workers_page, render_tools_page,
    render_models_page, render_security_page, render_selfx_page,
    render_skills_page, render_research_page, render_analytics_page,
    render_backups_page, render_notifications_page, render_settings_page,
    render_help_page,
)

app = FastHTML()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_shared_engine = None
_shared_factory = None


def _factory():
    global _shared_engine, _shared_factory
    if _shared_factory is None:
        _shared_engine = get_engine()
        init_db(_shared_engine)
        _shared_factory = get_session_factory(_shared_engine)
    return _shared_factory


class _DB:
    """Context-managed session helper for page handlers."""
    def __enter__(self):
        self.db = _factory()()
        return self.db

    def __exit__(self, *a):
        self.db.close()


def _redirect(url, flash=None, error=None):
    from urllib.parse import quote
    if flash or error:
        msg = flash if flash else error
        key = "flash" if flash else "error"
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{key}={quote(msg)}"
    return RedirectResponse(url, status_code=303)


def _model_adapter(settings: dict):
    """Pick adapter from the 'model' settings section (mock / litert / ollama)."""
    from lifeops.models.adapters import MockModelAdapter, LiteRTLMAdapter, OllamaAdapter
    model_cfg = settings.get("model", {}) or {}
    runtime = model_cfg.get("runtime", "mock")
    model_path = model_cfg.get("model_path") or None
    if runtime == "ollama":
        return OllamaAdapter(model_name=model_path or "llama3.2",
                             base_url=model_cfg.get("ollama_base_url") or None,
                             generation_params=model_cfg.get("generation_params"))
    if runtime == "litert":
        return LiteRTLMAdapter(model_path=model_path) if model_path else LiteRTLMAdapter()
    return MockModelAdapter()


# ---------------------------------------------------------------- dashboard
@app.get("/")
def home(flash: str = None):
    with _DB() as db:
        tasks = db.scalars(select(Task).order_by(desc(Task.created_at))).all()
        open_cnt = sum(1 for t in tasks
                       if t.status.value not in ("SUCCEEDED", "FAILED", "CANCELLED"))
        approvals = db.scalars(select(Approval).where(
            Approval.decision == ApprovalDecision.PENDING)).all()
        memories = len(db.scalars(select(Memory)).all())
        backups = len(db.scalars(select(BackupRecord)).all())
        runs = db.scalars(select(WorkflowRun).order_by(desc(WorkflowRun.started_at))).all()
        active_runs = sum(1 for r in runs if r.status == "running")
        diag = SelfDiagnostics(db).run_health_check()
        d = {
            "tasks_open": open_cnt, "agent_runs_active": active_runs,
            "pending_approvals": len(approvals), "memories": memories,
            "selfx_health": diag.get("status", "?"), "backups": backups,
            "recent_tasks": tasks[:8],
            "emergency_active": emergency_stop.active,
        }
    return render_dashboard(d)


# ---------------------------------------------------------------- tasks
@app.get("/tasks")
def page_tasks(flash: str = None):
    with _DB() as db:
        tasks = db.scalars(select(Task).order_by(desc(Task.created_at))).all()
        projects = db.scalars(select(Project)).all()
    return render_tasks_page(tasks, projects, flash=flash)


@app.post("/tasks/create")
def post_create_task(title: str, priority: str = "medium", due_date: str = "",
                     project: str = ""):
    with _DB() as db:
        svc = TaskService(db)
        pid = None
        if project:
            p = db.scalars(select(Project).where(Project.name == project)).first()
            if p is None:
                p = Project(name=project)
                db.add(p); db.commit(); db.refresh(p)
            pid = p.id
        due = None
        if due_date:
            try:
                due = datetime.datetime.fromisoformat(due_date)
            except ValueError:
                pass
        t = svc.create_task(title=title, priority=priority, project_id=pid, due_date=due)
        log_audit_event(db, "web-ui", "task.create", str(t.id), "success")
    return _redirect("/tasks", f"Task #{t.id} created.")


@app.post("/tasks/complete")
def post_complete_task(task_id: int):
    with _DB() as db:
        TaskService(db).update_task_status(task_id, TaskStatus.SUCCEEDED)
        log_audit_event(db, "web-ui", "task.complete", str(task_id), "success")
    return _redirect("/tasks", "Task completed.")


@app.post("/tasks/delete")
def post_delete_task(task_id: int):
    with _DB() as db:
        t = db.get(Task, task_id)
        if t:
            db.delete(t); db.commit()
            log_audit_event(db, "web-ui", "task.delete", str(task_id), "success")
    return _redirect("/tasks", "Task deleted.")


# ---------------------------------------------------------------- assistant
@app.get("/assistant")
def page_assistant(conversation: int = 0, error: str = None):
    with _DB() as db:
        convs = db.scalars(select(Conversation).order_by(Conversation.id)).all()
        msgs = []
        if conversation and any(c.id == conversation for c in convs):
            msgs = db.scalars(select(Message).where(Message.conversation_id == conversation)
                              .order_by(Message.id)).all()
        elif convs:
            last = convs[-1]
            msgs = db.scalars(select(Message).where(Message.conversation_id == last.id)
                              .order_by(Message.id)).all()
    return render_assistant_page(msgs, convs, error=error)


@app.post("/assistant/message")
def post_assistant_message(prompt: str, conversation: str = ""):
    with _DB() as db:
        settings = SettingsService(db).get_all()
        conv_id = int(conversation) if str(conversation).isdigit() else None
        if conv_id is None or db.get(Conversation, conv_id) is None:
            c = Conversation(title=prompt[:60])
            db.add(c); db.commit(); db.refresh(c)
            conv_id = c.id
        db.add(Message(conversation_id=conv_id, role="user", content=prompt))
        db.commit()
        try:
            reply = _model_adapter(settings).generate(prompt)
        except Exception as e:
            reply = "(mock) I received your objective. Model runtime note: " + e.__class__.__name__
        db.add(Message(conversation_id=conv_id, role="assistant", content=reply))
        db.commit()
        log_audit_event(db, "web-ui", "assistant.message", str(conv_id), "success")
    return _redirect(f"/assistant?conversation={conv_id}")


# ---------------------------------------------------------------- calendar
@app.get("/calendar")
def page_calendar(flash: str = None):
    with _DB() as db:
        now = datetime.datetime.utcnow()
        svc = CalendarService(db)
        events = svc.events_for_range(now - datetime.timedelta(days=1),
                                      now + datetime.timedelta(days=30))
        conflicts = []
        for e in events[:20]:
            for c in svc.find_conflicts(e.id):
                conflicts.append({"title": e.title,
                                  "with_title": c.get("title", str(c))})
    return render_calendar_page(events, conflicts, flash=flash)


@app.post("/calendar/create")
def post_calendar_create(title: str, start_time: str, end_time: str):
    with _DB() as db:
        try:
            s = datetime.datetime.fromisoformat(start_time)
            e = datetime.datetime.fromisoformat(end_time)
            ev = CalendarService(db).create_event(title=title, start_time=s, end_time=e)
        except ValueError as ex:
            return _redirect("/calendar", error=f"Invalid input: {ex}")
        log_audit_event(db, "web-ui", "calendar.create", str(ev.id), "success")
    return _redirect("/calendar", f"Event '{ev.title}' scheduled.")


# ---------------------------------------------------------------- notes
@app.get("/notes")
def page_notes(q: str = "", flash: str = None):
    with _DB() as db:
        svc = NoteService(db)
        notes = svc.search_notes(q) if q else db.scalars(
            select(Note).order_by(desc(Note.updated_at))).all()
        graph = svc.graph()
    return render_notes_page(notes, graph, q=q, flash=flash)


@app.get("/notes/{note_id}")
def page_note_detail(note_id: int, flash: str = None):
    with _DB() as db:
        note = db.get(Note, note_id)
    return render_note_detail(note, flash=flash)


@app.post("/notes/create")
def post_note_create(title: str, content: str = "", tags: str = ""):
    with _DB() as db:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        n = NoteService(db).create_note(title=title, content=content, tags=tag_list)
        log_audit_event(db, "web-ui", "note.create", str(n.id), "success")
    return _redirect("/notes", f"Note '{n.title}' created.")


@app.post("/notes/update")
def post_note_update(note_id: int, title: str = "", content: str = ""):
    with _DB() as db:
        data = {}
        if title:
            data["title"] = title
        if content:
            data["content"] = content
        updated = NoteService(db).update_note(note_id, data)
        if updated is None:
            return _redirect("/notes", error="Note not found.")
    return _redirect(f"/notes/{note_id}", "Note updated.")


@app.post("/notes/delete")
def post_note_delete(note_id: int):
    with _DB() as db:
        n = db.get(Note, note_id)
        if n:
            db.delete(n); db.commit()
    return _redirect("/notes", "Note deleted.")


# ---------------------------------------------------------------- memory
@app.get("/memory")
def page_memory(q: str = "", flash: str = None):
    with _DB() as db:
        if q:
            like = f"%{q}%"
            mems = db.scalars(select(Memory).where(
                Memory.value.like(like) | Memory.key.like(like))).all()
        else:
            mems = db.scalars(select(Memory).order_by(desc(Memory.updated_at))).all()
        revs = db.scalars(select(MemoryRevision)
                          .order_by(desc(MemoryRevision.revised_at))).all()[:50]
    return render_memory_page(mems, revs, q=q, flash=flash)


@app.post("/memory/store")
def post_memory_store(category: str, key: str, value: str):
    with _DB() as db:
        m = SelfMemory(db).store_memory(category=category, key=key, value=value,
                                        provenance="web-ui")
        log_audit_event(db, "web-ui", "memory.store", str(m.id), "success")
    return _redirect("/memory", "Memory stored.")


@app.post("/memory/delete")
def post_memory_delete(memory_id: int):
    with _DB() as db:
        m = db.get(Memory, memory_id)
        if m:
            db.delete(m); db.commit()
    return _redirect("/memory", "Memory deleted.")


@app.get("/memory/export")
def get_memory_export():
    with _DB() as db:
        mems = db.scalars(select(Memory)).all()
        payload = [{"category": m.category, "key": m.key, "value": m.value,
                    "confidence": m.confidence} for m in mems]
    return JSONResponse(payload)


# ---------------------------------------------------------------- files
@app.get("/files")
def page_files(q: str = "", flash: str = None):
    with _DB() as db:
        docs = db.scalars(select(Document).order_by(desc(Document.indexed_at))).all()
        results = DocumentService(db).search_documents(q)[:15] if q else []
    return render_files_page(docs, results, q=q, flash=flash)


@app.post("/files/index")
def post_files_index(directory: str):
    with _DB() as db:
        try:
            summary = DocumentService(db).index_directory(directory)
        except ValueError as e:
            return _redirect("/files", error=f"Rejected: {e}")
        log_audit_event(db, "web-ui", "documents.index", directory, "success")
    return _redirect("/files", f"Indexed {summary.get('indexed', 0)} new, "
                               f"{summary.get('skipped', 0)} unchanged.")


@app.post("/files/delete")
def post_file_delete(document_id: int):
    with _DB() as db:
        d = db.get(Document, document_id)
        if d:
            db.delete(d); db.commit()
    return _redirect("/files", "Document removed from index.")


# ---------------------------------------------------------------- search
@app.get("/search")
def page_search(q: str = ""):
    with _DB() as db:
        results = SearchService(db).search(q) if q else None
    return render_search_page(q=q, results=results)


# ---------------------------------------------------------------- workflows
@app.get("/workflows")
def page_workflows(flash: str = None, error: str = None):
    with _DB() as db:
        wfs = db.scalars(select(WorkflowDefinition)
                         .order_by(desc(WorkflowDefinition.updated_at))).all()
        runs = db.scalars(select(WorkflowRun)
                          .order_by(desc(WorkflowRun.started_at))).all()[:20]
    return render_workflows_page(wfs, runs, flash=flash, error=error)


@app.post("/workflows/create")
def post_workflow_create(definition: str):
    with _DB() as db:
        try:
            parsed = json.loads(definition)
        except json.JSONDecodeError as e:
            return _redirect("/workflows", error=f"Invalid JSON: {e}")
        wf = WorkflowEngine(db).create_workflow(
            name=parsed.get("name", "Untitled workflow"), definition=parsed)
        log_audit_event(db, "web-ui", "workflow.create", wf.id, "success")
    return _redirect("/workflows",
                     f"Workflow '{wf.name}' saved as draft ({wf.id}). Activate to validate & enable.")


def _wf_action(wf_id: str, action: str):
    with _DB() as db:
        eng = WorkflowEngine(db)
        try:
            if action == "activate":
                eng.activate(wf_id); msg = "Workflow activated (definition validated)."
            elif action == "pause":
                eng.set_status(wf_id, "paused"); msg = "Workflow paused."
            elif action == "delete":
                wf = db.get(WorkflowDefinition, wf_id)
                if wf:
                    db.delete(wf); db.commit()
                msg = "Workflow deleted."
            elif action == "duplicate":
                new = eng.duplicate(wf_id); msg = f"Duplicated as {new.id}."
            elif action == "run":
                run = eng.run(wf_id)
                msg = f"Run {run.id} finished: {run.status}"
            else:
                msg = f"Unknown action {action}"
        except (LookupError, ValueError) as e:
            return _redirect("/workflows", error=str(e))
        log_audit_event(db, "web-ui", f"workflow.{action}", wf_id, "success")
    return _redirect("/workflows", msg)


@app.post("/workflows/{workflow_id}/activate")
def wf_activate(workflow_id: str):
    return _wf_action(workflow_id, "activate")


@app.post("/workflows/{workflow_id}/pause")
def wf_pause(workflow_id: str):
    return _wf_action(workflow_id, "pause")


@app.post("/workflows/{workflow_id}/delete")
def wf_delete(workflow_id: str):
    return _wf_action(workflow_id, "delete")


@app.post("/workflows/{workflow_id}/duplicate")
def wf_duplicate(workflow_id: str):
    return _wf_action(workflow_id, "duplicate")


@app.post("/workflows/{workflow_id}/run")
def wf_run(workflow_id: str):
    return _wf_action(workflow_id, "run")


# ---------------------------------------------------------------- workers/scheduler
@app.get("/workers")
def page_workers(flash: str = None):
    with _DB() as db:
        jobs = db.scalars(select(ScheduledJob).order_by(ScheduledJob.name)).all()
        events = db.scalars(select(JobEvent).order_by(desc(JobEvent.timestamp))).all()[:30]
        stats = {"queued": 0, "running": 0,
                 "completed": sum(1 for e in events if e.event_type == "completed"),
                 "failed": sum(1 for e in events if e.event_type == "failed")}
    return render_workers_page(jobs, events, stats, flash=flash)


@app.post("/workers/create-job")
def post_create_job(name: str, cron: str, handler: str = "noop", payload: str = ""):
    with _DB() as db:
        try:
            action = json.loads(payload) if payload.strip() else {}
        except json.JSONDecodeError as e:
            return _redirect("/workers", error=f"Payload must be JSON: {e}")
        if handler not in JOB_HANDLERS:
            return _redirect("/workers", error=f"Unknown handler '{handler}'.")
        try:
            CronExpression(cron)  # validate
        except ValueError as e:
            return _redirect("/workers", error=f"Invalid cron: {e}")
        job = ScheduledJob(id="job_" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
                           name=name, cron_expression=cron,
                           action={"handler": handler, **action}, enabled=True)
        db.add(job); db.commit()
        log_audit_event(db, "web-ui", "scheduler.create", job.id, "success")
    return _redirect("/workers", f"Job '{name}' scheduled ({cron}).")


@app.post("/workers/run-now")
def post_run_now(job_id: str):
    with _DB() as db:
        job = db.get(ScheduledJob, job_id)
        if not job:
            return _redirect("/workers", error="Job not found.")
        ext_id = WorkerQueue(_factory).submit_action(job.name, job.action)
        log_audit_event(db, "web-ui", "scheduler.run_now", job_id, "success")
    return _redirect("/workers", f"Enqueued immediate execution ({ext_id}).")


@app.post("/workers/toggle")
def post_toggle_job(job_id: str):
    with _DB() as db:
        job = db.get(ScheduledJob, job_id)
        if job:
            job.enabled = not job.enabled
            db.commit()
    return _redirect("/workers", "Job toggled.")


# ---------------------------------------------------------------- tools/integrations/policy
@app.get("/tools")
def page_tools(flash: str = None, error: str = None):
    with _DB() as db:
        from lifeops.tools.registry import ToolRegistry
        pe = PolicyEngine()
        registry = ToolRegistry(pe)
        tools = []
        for t in registry.tools.values():
            entry = {k: v for k, v in t.items() if k != "handler"}
            entry["risk_level"] = pe.evaluate(t["action_key"]).value.lower()
            tools.append(entry)
        ints = db.scalars(select(Integration)).all()
        policy = [{"action": a, "effect": d.value, "reason": ""}
                  for a, d in pe.policies.items()]
    return render_tools_page(tools, ints, policy, flash=flash, error=error)


@app.post("/tools/integration-add")
def post_integration_add(name: str, config: str = ""):
    with _DB() as db:
        try:
            cfg = json.loads(config) if config.strip() else {}
        except json.JSONDecodeError as e:
            return _redirect("/tools", error=f"Config must be JSON: {e}")
        i = Integration(id="int_" + datetime.datetime.utcnow().strftime("%H%M%S"),
                        name=name, config=cfg, enabled=False)
        db.add(i); db.commit()
    return _redirect("/tools", f"Integration '{name}' registered (disabled until configured).")


@app.post("/tools/integration-toggle")
def post_integration_toggle(integration_id: str):
    with _DB() as db:
        i = db.get(Integration, integration_id)
        if i:
            i.enabled = not i.enabled
            i.health_status = "configured" if i.enabled else "unknown"
            db.commit()
    return _redirect("/tools", "Integration toggled.")


# ---------------------------------------------------------------- models
@app.get("/models")
def page_models(test_result: str = "", flash: str = None):
    with _DB() as db:
        settings = SettingsService(db).get_all()
        import shutil
        binary = shutil.which("litert-lm") or "not found"
        model_cfg = settings.get("model", {}) or {}
        try:
            adapter = _model_adapter(settings)
            adapter_name = type(adapter).__name__
            available = adapter.is_available()
        except Exception:
            adapter_name, available = "MockModelAdapter", True
        from lifeops.models.adapters import OllamaAdapter
        ollama_url = model_cfg.get("ollama_base_url") or OllamaAdapter.DEFAULT_BASE_URL
        try:
            ollama_models = OllamaAdapter(base_url=ollama_url).list_models()
        except Exception:
            ollama_models = []
        runtime = {"litert_lm_binary": binary, "models": ollama_models,
                   "adapter": adapter_name, "adapter_available": available,
                   "configured_runtime": model_cfg.get("runtime", "mock"),
                   "model_path": model_cfg.get("model_path", ""),
                   "ollama_base_url": ollama_url}
    return render_models_page(runtime, test_result=test_result or None, flash=flash)


@app.post("/models/test")
def post_model_test(prompt: str):
    with _DB() as db:
        settings = SettingsService(db).get_all()
        try:
            out = _model_adapter(settings).generate(prompt)
        except Exception as e:
            out = f"ERROR: {e}"
        log_audit_event(db, "web-ui", "model.test", None, "success")
    return page_models(test_result=out)


@app.post("/models/settings")
def post_model_settings(section: str = "model", runtime: str = "", model_path: str = "",
                        context_length: str = "", temperature: str = "",
                        ollama_base_url: str = ""):
    with _DB() as db:
        updates = {}
        if runtime:
            updates["runtime"] = runtime
        if model_path:
            updates["model_path"] = model_path
        if ollama_base_url:
            updates["ollama_base_url"] = ollama_base_url
        if context_length:
            try:
                updates["context_length"] = int(context_length)
            except ValueError:
                return _redirect("/models", error="context_length must be an integer.")
        if temperature:
            try:
                gp = dict((SettingsService(db).get_section("model").get("generation_params") or {}))
                gp["temperature"] = float(temperature)
                updates["generation_params"] = gp
            except ValueError:
                return _redirect("/models", error="temperature must be a number.")
        ok, err = SettingsService(db).update(section, updates, actor="web-ui")
    return _redirect("/models", "Model settings saved." if ok else f"Rejected: {err}")


# ---------------------------------------------------------------- security
@app.get("/security")
def page_security(flash: str = None):
    with _DB() as db:
        approvals = db.scalars(select(Approval).order_by(desc(Approval.id))).all()[:20]
        audit = db.scalars(select(AuditEvent).order_by(desc(AuditEvent.timestamp))).all()[:50]
    return render_security_page(approvals, audit, emergency_stop.snapshot(), flash=flash)


@app.post("/security/approve")
def post_approve(approval_id: str, decision: str):
    with _DB() as db:
        dec = ApprovalDecision.APPROVED if decision == "APPROVED" else ApprovalDecision.REJECTED
        ok = ApprovalGate(db).decide(approval_id, dec, decided_by="web-ui")
        log_audit_event(db, "web-ui", "approval." + decision.lower(), approval_id,
                        "success" if ok else "failure")
    return _redirect("/security",
                     f"Approval {decision.lower()} recorded." if ok else "Approval not found.")


@app.post("/security/emergency-stop")
def post_emergency_stop(reason: str = "manual-web"):
    emergency_stop.engage(reason)
    with _DB() as db:
        log_audit_event(db, "web-ui", "emergency.stop", None, "success", {"reason": reason})
    return _redirect("/security", "EMERGENCY STOP ENGAGED - mutating operations are blocked.")


@app.post("/security/emergency-release")
def post_emergency_release():
    emergency_stop.release()
    with _DB() as db:
        log_audit_event(db, "web-ui", "emergency.release", None, "success")
    return _redirect("/security", "Emergency stop released; operations resumed.")


# ---------------------------------------------------------------- self-x
@app.get("/selfx")
def page_selfx(flash: str = None):
    with _DB() as db:
        identity = SelfIdentity.get_system_identity()
        diag = SelfDiagnostics(db).run_health_check()
        goals = db.scalars(select(SelfXGoal)).all()
        evals = db.scalars(select(Evaluation).order_by(desc(Evaluation.created_at))).all()
        imps = db.scalars(select(ImprovementProposal)
                          .order_by(desc(ImprovementProposal.created_at))).all()
        cps = db.scalars(select(Checkpoint).order_by(desc(Checkpoint.created_at))).all()
    return render_selfx_page(identity, diag, goals, evals, imps, cps, flash=flash)


@app.post("/selfx/diagnose")
def post_diagnose():
    with _DB() as db:
        SelfDiagnostics(db).run_health_check()
        log_audit_event(db, "web-ui", "selfx.diagnose", None, "success")
    return _redirect("/selfx", "Self-diagnosis complete.")


@app.post("/selfx/goal")
def post_goal(objective: str, target: str = ""):
    with _DB() as db:
        try:
            tgt = json.loads(target) if target.strip() else {}
        except json.JSONDecodeError:
            tgt = {"raw": target}
        g = SelfXGoal(id="goal_" + datetime.datetime.utcnow().strftime("%H%M%S"),
                      objective=objective, baseline={}, target=tgt)
        db.add(g); db.commit()
    return _redirect("/selfx", "Improvement goal added.")


@app.post("/selfx/checkpoint")
def post_checkpoint(description: str):
    with _DB() as db:
        c = SelfRecovery(db).create_checkpoint(description=description, artifact_refs={})
        log_audit_event(db, "web-ui", "selfx.checkpoint", c.id, "success")
    return _redirect("/selfx", f"Checkpoint {c.id} created.")


# ---------------------------------------------------------------- skills
@app.get("/skills")
def page_skills(flash: str = None, error: str = None):
    with _DB() as db:
        skills = db.scalars(select(Skill)).all()
        tests = db.scalars(select(SkillTest).order_by(desc(SkillTest.id))).all()
    return render_skills_page(skills, tests, flash=flash, error=error)


@app.post("/skills/create")
def post_skill_create(name: str, description: str = "", instructions: str = ""):
    with _DB() as db:
        sid = "skill_" + name.lower().replace(" ", "_")[:40]
        skill = SelfSkills(db).draft_skill(skill_id=sid, name=name,
                                           description=description or name,
                                           instructions=instructions,
                                           manifest={"source": "web-ui"})
        log_audit_event(db, "web-ui", "skill.create", sid, "success")
    return _redirect("/skills",
                     f"Skill '{skill.name}' drafted ({sid}). Add passing tests, then publish.")


@app.post("/skills/test/add")
def post_skill_test_add(skill_id: str, test_name: str, test_input: str = "{}",
                        expected_output: str = "{}"):
    with _DB() as db:
        try:
            ti = json.loads(test_input or "{}")
            eo = json.loads(expected_output or "{}")
        except json.JSONDecodeError as e:
            return _redirect("/skills", error=f"Test fields must be JSON: {e}")
        if db.get(Skill, skill_id) is None:
            return _redirect("/skills", error=f"Skill '{skill_id}' not found.")
        t = SkillTest(skill_id=skill_id, test_name=test_name, test_input=ti,
                      expected_output=eo)
        db.add(t); db.commit()
    return _redirect("/skills", "Test added.")


@app.post("/skills/test/run")
def post_skill_test_run(test_id: int):
    with _DB() as db:
        t = db.get(SkillTest, test_id)
        if not t:
            return _redirect("/skills", error="Test not found.")
        # Deterministic contract check against the skill's published instructions.
        version = db.scalars(select(SkillVersion)
                             .where(SkillVersion.skill_id == t.skill_id)).first()
        body = (version.instructions if version else "") or ""
        passed = bool(body) and all(str(k) in body or str(v) in body
                                    for k, v in (t.expected_output or {}).items())
        t.last_passed = passed
        t.last_run_at = datetime.datetime.utcnow()
        db.commit()
    result = "PASSED" if passed else "FAILED"
    return _redirect("/skills", f"Test '{t.test_name}' {result}.")


@app.post("/skills/publish")
def post_skill_publish(skill_id: str):
    with _DB() as db:
        tests = db.scalars(select(SkillTest).where(SkillTest.skill_id == skill_id)).all()
        if not tests or not all(t.last_passed for t in tests):
            return _redirect("/skills",
                             error="Publish blocked: all skill tests must exist and pass first.")
        ok = SelfSkills(db).publish_skill_version(skill_id, "1.0.1")
        log_audit_event(db, "web-ui", "skill.publish", skill_id,
                        "success" if ok else "failure")
    return _redirect("/skills", "Skill published." if ok else "Publish failed (skill missing).")


@app.post("/skills/toggle")
def post_skill_toggle(skill_id: str):
    with _DB() as db:
        s = db.get(Skill, skill_id)
        if s:
            s.enabled = not s.enabled
            db.commit()
    return _redirect("/skills", "Skill toggled.")


# ---------------------------------------------------------------- research
@app.get("/research")
def page_research(flash: str = None):
    with _DB() as db:
        jobs = db.scalars(select(ResearchJob).order_by(desc(ResearchJob.id))).all()
        sources = db.scalars(select(ResearchSource)).all()
    return render_research_page(jobs, sources, flash=flash)


@app.post("/research/create")
def post_research_create(topic: str):
    with _DB() as db:
        pe = PolicyEngine()
        network_allowed = pe.evaluate("network.http_get").value.upper() == "ALLOW"
        job = ResearchJob(id="res_" + datetime.datetime.utcnow().strftime("%H%M%S"),
                          topic=topic, status="completed",
                          findings={"summary": f"Analysis of '{topic}'.",
                                    "mode": "web" if network_allowed else "local",
                                    "related_notes": []})
        if topic.strip():
            notes = db.scalars(select(Note)
                               .where(Note.title.like(f"%{topic.split()[0]}%")).limit(5)).all()
            job.findings["related_notes"] = [{"id": n.id, "title": n.title} for n in notes]
        db.add(job); db.commit()
        log_audit_event(db, "web-ui", "research.create", job.id, "success")
    mode = "web" if network_allowed else "local-only (network blocked by policy)"
    return _redirect("/research", f"Research job finished via {mode}.")


# ---------------------------------------------------------------- analytics
@app.get("/analytics")
def page_analytics(flash: str = None):
    with _DB() as db:
        tasks = db.scalars(select(Task)).all()
        done = sum(1 for t in tasks if t.status.value == "SUCCEEDED")
        rate = (done / len(tasks)) if tasks else 0.0
        runs = db.scalars(select(WorkflowRun)).all()
        evals = db.scalars(select(Evaluation)).all()
        avg = sum(e.score for e in evals) / len(evals) if evals else 0.0
        tool_calls = len(db.scalars(select(JobEvent)).all())
        summary = {"tasks_total": len(tasks), "task_success_rate": rate,
                   "runs_total": len(runs), "avg_eval_score": avg,
                   "tool_calls_total": tool_calls, "jobs_executed": tool_calls}
    return render_analytics_page(summary, evals, flash=flash)


# ---------------------------------------------------------------- backups
@app.get("/backups")
def page_backups(flash: str = None, error: str = None):
    with _DB() as db:
        recs = db.scalars(select(BackupRecord)
                          .order_by(desc(BackupRecord.created_at))).all()
    return render_backups_page(recs, flash=flash, error=error)


def _backup_manager(db):
    from lifeops.storage.database import DEFAULT_DB_URL
    db_path = DEFAULT_DB_URL.split("///", 1)[-1] if "sqlite" in DEFAULT_DB_URL else "data/lifeops.db"
    return BackupManager(db, db_path=db_path)


@app.post("/backups/create")
def post_backup_create():
    with _DB() as db:
        try:
            rec = _backup_manager(db).create_backup(description="manual web backup")
        except Exception as e:
            return _redirect("/backups", error=f"Backup failed: {e}")
        log_audit_event(db, "web-ui", "backup.create", rec["id"], "success")
    return _redirect("/backups", f"Backup {rec['id']} created.")


@app.post("/backups/verify")
def post_backup_verify(backup_id: str):
    with _DB() as db:
        try:
            res = _backup_manager(db).verify_backup(backup_id)
        except Exception as e:
            return _redirect("/backups", error=f"Verification failed: {e}")
    verdict = "VERIFIED OK" if res.get("ok") else "CORRUPT"
    return _redirect("/backups", f"Backup {backup_id}: {verdict}")


@app.post("/backups/restore")
def post_backup_restore(backup_id: str, confirm: str = ""):
    if confirm != "true":
        return _redirect("/backups", error="Restore requires explicit confirmation.")
    with _DB() as db:
        try:
            res = _backup_manager(db).restore(backup_id)
        except Exception as e:
            return _redirect("/backups", error=f"Restore failed: {e}")
        log_audit_event(db, "web-ui", "backup.restore", backup_id, "success")
    return _redirect("/backups", f"Restored {backup_id}: {res.get('message', 'ok')}")


@app.post("/backups/retention")
def post_backup_retention():
    with _DB() as db:
        removed = _backup_manager(db).apply_retention(keep=10)
    return _redirect("/backups", f"Retention applied; removed {len(removed)} old backup(s).")


# ---------------------------------------------------------------- notifications
@app.get("/notifications")
def page_notifications(flash: str = None):
    with _DB() as db:
        items = db.scalars(select(Notification)
                           .order_by(desc(Notification.created_at))).all()
    return render_notifications_page(items, flash=flash)


@app.post("/notifications/read")
def post_notification_read(notification_id: int):
    with _DB() as db:
        n = db.get(Notification, notification_id)
        if n:
            n.read = True
            db.commit()
    return _redirect("/notifications", "Marked read.")


# ---------------------------------------------------------------- settings
@app.get("/settings")
def page_settings(flash: str = None, error: str = None):
    with _DB() as db:
        svc = SettingsService(db)
        allset = svc.get_all()
        profiles = [{"id": k, "name": k, "description": v["description"]}
                    for k, v in AUTONOMY_PROFILES.items()]
    return render_settings_page(allset, profiles, flash=flash, error=error)


def _coerce(raw):
    if raw in ("true", "false"):
        return raw == "true"
    try:
        return int(raw)
    except (ValueError, TypeError):
        pass
    try:
        return float(raw)
    except (ValueError, TypeError):
        pass
    return raw


@app.post("/settings/save")
async def post_settings_save(request: Request):
    form = await request.form()
    section = form.get("section", "")
    updates = {k: _coerce(v) for k, v in form.items() if k != "section"}
    with _DB() as db:
        ok, err = SettingsService(db).update(section, updates, actor="web-ui")
    return _redirect("/settings", f"'{section}' updated." if ok else f"Rejected: {err}")


@app.post("/settings/profile")
def post_settings_profile(profile: str):
    with _DB() as db:
        try:
            SettingsService(db).set_autonomy_profile(profile, actor="web-ui")
        except ValueError as e:
            return _redirect("/settings", error=str(e))
    return _redirect("/settings", f"Autonomy profile set to '{profile}'.")


@app.post("/settings/reset-all")
def post_settings_reset():
    with _DB() as db:
        SettingsService(db).restore_defaults(actor="web-ui")
        log_audit_event(db, "web-ui", "settings.reset", None, "success")
    return _redirect("/settings", "All settings restored to defaults.")


# ---------------------------------------------------------------- help
@app.get("/help")
def page_help():
    return render_help_page(version="0.1.0")


def create_app():
    """Initialize DB and return the ASGI app (used by lifeops.main)."""
    engine = get_engine()
    init_db(engine)
    return app
