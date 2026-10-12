"""Browser-first LifeOps application. Binds to loopback by default."""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from html import escape
from fasthtml.common import FastHTML
import uvicorn
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route
from . import __version__
from .database import init_db, get_session_factory, Task, AuditEvent
from .services import create_task, list_tasks, complete_task, create_note, list_notes, create_project, list_projects, create_memory, search_memories, create_approval, list_approvals, decide_approval, create_agent_run, create_self_goal, create_improvement_proposal, decide_improvement_proposal, ValidationError

@asynccontextmanager
async def lifespan(app):
    engine = init_db()
    from .storage.models import Base as StorageBase
    StorageBase.metadata.create_all(bind=engine)
    yield

def page(title: str, body: str) -> HTMLResponse:
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark light"><title>{escape(title)} · LifeOps</title><link rel="stylesheet" href="/static/app.css"></head><body><aside class="sidebar"><a class="brand" href="/">◈ LifeOps <span>SELF-X</span></a><nav><a href="/">Overview</a><a href="/tasks">Tasks</a><a href="/notes">Notes & Knowledge</a><a href="/projects">Projects</a><a href="/memory">Memory Explorer</a><a href="/approvals">Approvals</a><a href="/selfx">Self-X Diagnostics</a><a href="/settings">Settings</a></nav><div class="local-tag">● Local-first workspace</div></aside><main><header><div><p class="eyebrow">PERSONAL OPERATING SYSTEM</p><h1>{escape(title)}</h1></div><span class="pill">v{__version__}</span></header>{body}<footer>LifeOps AI + Self-X · Your data stays on this machine by default.</footer></main></body></html>'''
    return HTMLResponse(html)

def db_session(): return get_session_factory()()

async def home(request):
    with db_session() as db:
        tasks=list_tasks(db); notes=list_notes(db); opened=sum(t.status=="open" for t in tasks); completed=sum(t.status=="completed" for t in tasks)
    body=f'''<section class="hero"><div><p class="eyebrow">YOUR DAY, UNDER CONTROL</p><h2>Make progress. Keep your context.</h2><p>One private workspace for tasks, knowledge, and controlled AI evolution.</p><a class="button" href="/tasks">Manage tasks ↗</a></div><div class="orb">L<span>✳</span></div></section><section class="stats"><article class="stat"><span>Open tasks</span><strong>{opened}</strong><small>Ready for your focus</small></article><article class="stat"><span>Completed</span><strong>{completed}</strong><small>Progress recorded</small></article><article class="stat"><span>Knowledge notes</span><strong>{len(notes)}</strong><small>Stored locally</small></article><article class="stat"><span>AI runtime</span><strong class="muted">Not configured</strong><small>Productivity works without a model</small></article></section><section class="panel"><div class="section-heading"><div><p class="eyebrow">WORK QUEUE</p><h2>Recent tasks</h2></div><a href="/tasks">View all →</a></div>{task_list(tasks[:5])}</section><section class="panel"><div class="section-heading"><div><p class="eyebrow">SYSTEM STATUS</p><h2>Foundation health</h2></div><a href="/selfx">Run diagnostics →</a></div><p class="health"><span class="dot"></span> Web application active <span class="dot"></span> SQLite persistence enabled <span class="dot warn"></span> AI runtime not configured</p></section>'''
    return page("Overview",body)

def task_list(tasks):
    if not tasks: return '<div class="empty">No tasks yet. Add one above to get moving.</div>'
    items=[]
    for t in tasks:
        action='' if t.status=='completed' else f'<form method="post" action="/tasks/{t.id}/complete"><button class="icon-button" aria-label="Complete task">✓</button></form>'
        items.append(f'<div class="task-row"><div class="check {"done" if t.status=="completed" else ""}">{"✓" if t.status=="completed" else ""}</div><div class="task-copy"><strong>{escape(t.title)}</strong><small>{escape(t.description[:120])}</small></div><span class="priority {escape(t.priority)}">{escape(t.priority)}</span>{action}</div>')
    return ''.join(items)

async def tasks_page(request):
    with db_session() as db: tasks=list_tasks(db)
    body=f'''<section class="panel"><p class="eyebrow">CAPTURE IT, THEN DO IT</p><h2>New task</h2><form class="task-form" method="post" action="/tasks"><label>Task title<input name="title" maxlength="240" required placeholder="e.g. Review project roadmap"></label><label>Details<textarea name="description" rows="2" maxlength="10000" placeholder="Optional context"></textarea></label><label>Priority<select name="priority"><option value="medium">Medium</option><option value="high">High</option><option value="low">Low</option></select></label><button class="button" type="submit">＋ Add task</button></form></section><section class="panel"><div class="section-heading"><div><p class="eyebrow">YOUR WORK QUEUE</p><h2>All tasks <span class="count">{len(tasks)}</span></h2></div></div>{task_list(tasks)}</section>'''
    return page("Tasks & Projects",body)

async def create_task_route(request):
    form=await request.form()
    try:
        with db_session() as db: create_task(db,str(form.get("title","")),str(form.get("description","")),str(form.get("priority","medium")))
    except ValidationError as exc: return page("Tasks & Projects",f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/tasks">Back to tasks</a></section>')
    return RedirectResponse("/tasks",status_code=303)

async def complete_task_route(request):
    try:
        with db_session() as db: complete_task(db,int(request.path_params["task_id"]))
    except (ValueError,LookupError): return PlainTextResponse("Task not found",status_code=404)
    return RedirectResponse("/tasks",status_code=303)

async def notes_page(request):
    with db_session() as db: notes=list_notes(db)
    cards=''.join(f'<article class="note"><h3>{escape(n.title)}</h3><p>{escape(n.content[:600])}</p><small>Updated {n.updated_at.strftime("%Y-%m-%d %H:%M")}</small></article>' for n in notes) or '<div class="empty">Your knowledge base is ready. Create your first note.</div>'
    body=f'''<section class="panel"><p class="eyebrow">PERSONAL KNOWLEDGE</p><h2>Capture a useful thought</h2><form class="task-form" method="post" action="/notes"><label>Title<input name="title" required maxlength="240" placeholder="Note title"></label><label>Content<textarea name="content" rows="4" maxlength="100000" placeholder="Write a note in plain text or Markdown..."></textarea></label><button class="button" type="submit">Save note</button></form></section><section class="notes-grid">{cards}</section>'''
    return page("Notes & Knowledge",body)

async def create_note_route(request):
    form=await request.form()
    try:
        with db_session() as db: create_note(db,str(form.get("title","")),str(form.get("content","")))
    except ValidationError as exc: return page("Notes & Knowledge",f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/notes">Back to notes</a></section>')
    return RedirectResponse("/notes",status_code=303)

async def selfx_page(request):
    from .database import SelfGoal, Evaluation, ImprovementProposal
    with db_session() as db:
        task_count=len(list_tasks(db)); note_count=len(list_notes(db)); audit_count=db.query(AuditEvent).count()
        goals=db.query(SelfGoal).order_by(SelfGoal.id.desc()).limit(20).all()
        evaluations=db.query(Evaluation).order_by(Evaluation.id.desc()).limit(20).all()
        proposals=db.query(ImprovementProposal).order_by(ImprovementProposal.id.desc()).limit(20).all()
    goal_cards=''.join(f'<article class="note"><h3>{escape(g.title)}</h3><p>{escape(g.objective)}</p><small>Status: {escape(g.status)} · Baseline: {escape(g.baseline or "not set")} · Target: {escape(g.target or "not set")}</small></article>' for g in goals) or '<div class="empty">No improvement goals recorded.</div>'
    evaluation_cards=''.join(f'<article class="note"><h3>{escape(e.name)}</h3><p>Suite {escape(e.suite_version)} · Score: {("not scored" if e.score is None else format(e.score, ".3f"))}</p><small>{escape(e.details[:500])}</small></article>' for e in evaluations) or '<div class="empty">No evaluation records yet.</div>'
    proposal_cards=[]
    for p in proposals:
        card=f'<article class="note"><span class="priority {escape(p.risk if p.risk in {"low","medium","high"} else "high")}">{escape(p.risk)}</span><h3>{escape(p.title)}</h3><p>{escape(p.problem)}</p><small>Status: {escape(p.status)}</small>'
        if p.status == "proposed": card += f'<div class="approval-actions"><form method="post" action="/selfx/proposals/{p.id}/decision"><input type="hidden" name="decision" value="approve"><button class="button">Approve trial</button></form><form method="post" action="/selfx/proposals/{p.id}/decision"><input type="hidden" name="decision" value="reject"><button class="icon-button">Reject</button></form></div>'
        proposal_cards.append(card+'</article>')
    proposal_html=''.join(proposal_cards) or '<div class="empty">No improvement proposals recorded.</div>'
    body=f'''<section class="hero compact"><div><p class="eyebrow">SELF-X CONTROL CENTER</p><h2>Observe first. Improve safely.</h2><p>Record measurable goals, evaluation evidence, and reviewable proposals.</p></div><div class="orb">✳</div></section><section class="stats"><article class="stat"><span>Database</span><strong class="healthy">Connected</strong><small>SQLite session succeeded</small></article><article class="stat"><span>Tasks</span><strong>{task_count}</strong><small>Persistent records</small></article><article class="stat"><span>Notes</span><strong>{note_count}</strong><small>Persistent records</small></article><article class="stat"><span>Audit events</span><strong>{audit_count}</strong><small>Service actions recorded</small></article></section><section class="panel"><h2>Improvement goal</h2><form class="task-form" method="post" action="/selfx/goals"><label>Title<input name="title" maxlength="240" required></label><label>Objective<textarea name="objective" maxlength="5000" required></textarea></label><label>Baseline<input name="baseline" maxlength="5000"></label><label>Target<input name="target" maxlength="5000"></label><button class="button">Save goal</button></form></section><section class="notes-grid">{goal_cards}</section><section class="panel"><h2>Improvement proposal</h2><form class="task-form" method="post" action="/selfx/proposals"><label>Title<input name="title" maxlength="240" required></label><label>Problem<textarea name="problem" maxlength="10000" required></textarea></label><label>Evidence<textarea name="evidence" maxlength="10000"></textarea></label><label>Expected benefit<textarea name="expected_benefit" maxlength="10000"></textarea></label><label>Risk<select name="risk"><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></label><label>Rollback plan<textarea name="rollback_plan" maxlength="10000" required></textarea></label><button class="button">Submit proposal</button></form></section><section class="notes-grid">{proposal_html}</section><section class="panel"><h2>Evaluation history</h2>{evaluation_cards}<p class="hint">This page records evidence; it does not run repairs or deploy code. Approval permits only a separately sandboxed trial.</p></section>'''
    return page("Self-X Diagnostics",body)

async def create_goal_route(request):
    form=await request.form()
    try:
        with db_session() as db: create_self_goal(db,str(form.get("title","")),str(form.get("objective","")),str(form.get("baseline","")),str(form.get("target","")))
    except ValidationError as exc: return page("Self-X Diagnostics",f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/selfx">Back</a></section>')
    return RedirectResponse("/selfx",status_code=303)

async def create_proposal_route(request):
    form=await request.form()
    try:
        with db_session() as db: create_improvement_proposal(db,str(form.get("title","")),str(form.get("problem","")),str(form.get("evidence","")),str(form.get("expected_benefit","")),str(form.get("risk","medium")),str(form.get("rollback_plan","")))
    except ValidationError as exc: return page("Self-X Diagnostics",f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/selfx">Back</a></section>')
    return RedirectResponse("/selfx",status_code=303)

async def proposal_decision_route(request):
    form=await request.form()
    try:
        with db_session() as db: decide_improvement_proposal(db,int(request.path_params["proposal_id"]),approve=form.get("decision")=="approve",reason="Reviewed through local UI")
    except (ValueError,LookupError,ValidationError) as exc: return PlainTextResponse(str(exc),status_code=409)
    return RedirectResponse("/selfx",status_code=303)

async def settings_page(request):
    from .models.provider_catalog import list_provider_presets, PROVIDER_PRESETS
    from .storage.models import Setting
    presets = list_provider_presets()
    with db_session() as db:
        row = db.get(Setting, "model_provider")
        config = dict(row.value) if row and isinstance(row.value, dict) else {}
    selected = str(config.get("provider_id", "ollama"))
    model = str(config.get("model", ""))
    timeout = int(config.get("timeout_seconds", 60))
    endpoint = str(config.get("base_url_override", ""))
    options = "".join(
        f'<option value="{escape(p["id"])}" {"selected" if p["id"] == selected else ""}>{escape(p["id"])}</option>'
        for p in presets
    )
    body = f"""<section class="panel"><p class="eyebrow">MODEL MANAGER</p><h2>Provider configuration</h2>
    <p class="hint">Saving does not contact a provider. Credentials remain in your environment; this form never accepts or displays secret values.</p>
    <form class="task-form" method="post" action="/settings/model">
    <label>Provider<select name="provider_id" required>{options}</select></label>
    <label>Model identifier<input name="model" maxlength="240" required value="{escape(model)}" placeholder="Enter an installed or provider-supported model ID"></label>
    <label>Optional endpoint override<input name="base_url_override" maxlength="500" value="{escape(endpoint)}" placeholder="Leave blank to use provider default"></label>
    <label>Request timeout (seconds)<input name="timeout_seconds" type="number" min="1" max="120" value="{timeout}" required></label>
    <button class="button" type="submit">Save model settings</button></form>
    <div class="capability"><span>Selected provider</span><b>{escape(selected)}</b></div>
    <div class="capability"><span>Connection status</span><b class="muted">Not tested</b></div>
    <p class="hint">Hosted providers may transmit prompts outside this machine. Use local endpoints for private content. Custom endpoints are restricted to HTTP(S) loopback or explicitly preset hosted endpoints.</p>
    </section>"""
    return page("Settings", body)

async def save_model_settings(request):
    from datetime import datetime, timezone
    from .models.provider_catalog import PROVIDER_PRESETS
    from .storage.models import Setting
    form = await request.form()
    provider_id = str(form.get("provider_id", "")).strip().lower()
    model = str(form.get("model", "")).strip()
    endpoint = str(form.get("base_url_override", "")).strip()
    try:
        timeout = int(str(form.get("timeout_seconds", "60")))
        if provider_id not in PROVIDER_PRESETS:
            raise ValueError("Choose a supported provider preset.")
        if not model or len(model) > 240:
            raise ValueError("Model identifier must contain 1–240 characters.")
        if not 1 <= timeout <= 120:
            raise ValueError("Timeout must be between 1 and 120 seconds.")
        if endpoint:
            from urllib.parse import urlsplit
            parsed = urlsplit(endpoint)
            if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.port is None or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("Endpoint overrides must be explicit HTTP loopback URLs with a port and no credentials, query, or fragment.")
            if parsed.port < 1 or parsed.port > 65535:
                raise ValueError("Endpoint port is invalid.")
        safe = {"provider_id": provider_id, "model": model, "base_url_override": endpoint, "timeout_seconds": timeout}
        with db_session() as db:
            row = db.get(Setting, "model_provider")
            if row is None:
                db.add(Setting(key="model_provider", value=safe))
            else:
                row.value = safe
                row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            db.add(AuditEvent(event_type="settings.model_provider.updated", details=f"provider={provider_id};model_configured=true"))
            db.commit()
    except (ValueError, TypeError) as exc:
        return page("Settings", f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/settings">Back to settings</a></section>')
    return RedirectResponse("/settings", status_code=303)

async def projects_page(request):
    with db_session() as db: projects=list_projects(db)
    cards=''.join(f'<article class="note"><h3>{escape(p.name)}</h3><p>{escape(p.description)}</p><small>{escape(p.status)}</small><p><a href="/tasks">Manage tasks →</a></p></article>' for p in projects) or '<div class="empty">No projects yet. Create one to organize your work.</div>'
    body=f'<section class="panel"><h2>Create project</h2><form class="task-form" method="post" action="/projects"><label>Name<input name="name" required maxlength="160"></label><label>Description<textarea name="description" maxlength="5000" rows="3"></textarea></label><button class="button" type="submit">Create project</button></form></section><section class="notes-grid">{cards}</section>'
    return page("Projects",body)

async def create_project_route(request):
    form=await request.form()
    try:
        with db_session() as db: create_project(db,str(form.get("name","")),str(form.get("description","")))
    except ValidationError as exc: return page("Projects",f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/projects">Back</a></section>')
    return RedirectResponse("/projects",status_code=303)

async def memory_page(request):
    query=str(request.query_params.get("q",""))[:200]
    with db_session() as db: memories=search_memories(db,query)
    cards=''.join(f'<article class="note"><span class="priority medium">{escape(m.category)}</span><p>{escape(m.content)}</p><small>Source: {escape(m.source)} · confidence {m.confidence:.2f}</small><form method="post" action="/memory/{m.id}/delete"><button class="icon-button" type="submit">Delete</button></form></article>' for m in memories) or '<div class="empty">No memories match your search.</div>'
    body=f'<section class="panel"><h2>Store a memory</h2><form class="task-form" method="post" action="/memory"><label>Memory<textarea name="content" required maxlength="10000" rows="3"></textarea></label><label>Category<select name="category"><option>general</option><option>preference</option><option>project</option><option>procedure</option><option>lesson</option><option>research</option></select></label><button class="button" type="submit">Save memory</button></form><form method="get" action="/memory" class="task-form"><label>Search memories<input name="q" maxlength="200" value="{escape(query)}"></label><button class="button" type="submit">Search</button></form></section><section class="notes-grid">{cards}</section>'
    return page("Memory Explorer",body)

async def create_memory_route(request):
    form=await request.form()
    try:
        with db_session() as db: create_memory(db,str(form.get("content","")),str(form.get("category","general")))
    except ValidationError as exc: return page("Memory Explorer",f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/memory">Back</a></section>')
    return RedirectResponse("/memory",status_code=303)

async def delete_memory_route(request):
    from .services import delete_memory
    try:
        with db_session() as db: delete_memory(db,int(request.path_params["memory_id"]))
    except (ValueError,LookupError): return PlainTextResponse("Memory not found",status_code=404)
    return RedirectResponse("/memory",status_code=303)

async def approvals_page(request):
    with db_session() as db: items=list_approvals(db)
    cards=''.join(f'<article class="note"><span class="priority high">{escape(a.risk)}</span><h3>{escape(a.action)}</h3><p>{escape(a.summary)}</p><small>Pending human decision</small><div class="approval-actions"><form method="post" action="/approvals/{a.id}/decision"><input type="hidden" name="decision" value="approve"><button class="button" type="submit">Approve record</button></form><form method="post" action="/approvals/{a.id}/decision"><input type="hidden" name="decision" value="reject"><button class="icon-button" type="submit">Reject</button></form></div></article>' for a in items) or '<div class="empty">No pending approvals.</div>'
    body=f'<section class="panel"><p class="hint">Approval records do not execute actions. A separate policy-checked executor must verify an approved action before performing it.</p></section><section class="notes-grid">{cards}</section>'
    return page("Security & Approvals",body)

async def approval_decision_route(request):
    form=await request.form()
    try:
        with db_session() as db: decide_approval(db,int(request.path_params["approval_id"]),approve=form.get("decision")=="approve",actor="local-user",reason="Decision submitted through local UI")
    except (ValueError,LookupError,ValidationError) as exc: return PlainTextResponse(str(exc),status_code=409)
    return RedirectResponse("/approvals",status_code=303)

async def api_tasks(request):
    if request.method == "GET":
        with db_session() as db: rows=list_tasks(db)
        return JSONResponse({"items":[{"id":t.id,"title":t.title,"description":t.description,"priority":t.priority,"status":t.status,"project_id":t.project_id} for t in rows]})
    data=await request.json()
    try:
        with db_session() as db: t=create_task(db,str(data.get("title","")),str(data.get("description","")),str(data.get("priority","medium")))
        return JSONResponse({"id":t.id,"title":t.title,"status":t.status},status_code=201)
    except ValidationError as exc: return JSONResponse({"error":str(exc)},status_code=422)


async def api_approvals(request):
    if request.method == "GET":
        with db_session() as db:
            items=list_approvals(db, str(request.query_params.get("status","pending")))
        return JSONResponse({"items":[{"id":a.id,"action":a.action,"summary":a.summary,"risk":a.risk,"status":a.status} for a in items]})
    data=await request.json()
    try:
        with db_session() as db: a=create_approval(db,str(data.get("action","")),str(data.get("summary","")),str(data.get("risk","high")))
        return JSONResponse({"id":a.id,"status":a.status,"action":a.action},status_code=201)
    except ValidationError as exc: return JSONResponse({"error":str(exc)},status_code=422)

async def api_approval_decision(request):
    data=await request.json()
    try:
        with db_session() as db:
            item=decide_approval(db,int(request.path_params["approval_id"]),approve=bool(data.get("approve")),actor=str(data.get("actor","local-user")),reason=str(data.get("reason","")))
        return JSONResponse({"id":item.id,"status":item.status,"decided_at":item.decided_at.isoformat() if item.decided_at else None})
    except (ValueError,LookupError,ValidationError) as exc: return JSONResponse({"error":str(exc)},status_code=409)

async def api_memories(request):
    if request.method == "GET":
        with db_session() as db: rows=search_memories(db,str(request.query_params.get("q","")))
        return JSONResponse({"items":[{"id":m.id,"category":m.category,"content":m.content,"source":m.source,"confidence":m.confidence,"stale":m.stale} for m in rows]})
    data=await request.json()
    try:
        with db_session() as db: m=create_memory(db,str(data.get("content","")),str(data.get("category","general")),str(data.get("source","api")),float(data.get("confidence",1.0)))
        return JSONResponse({"id":m.id,"category":m.category},status_code=201)
    except (ValidationError,TypeError,ValueError) as exc: return JSONResponse({"error":str(exc)},status_code=422)

async def api_agent_runs(request):
    data=await request.json()
    try:
        with db_session() as db: run=create_agent_run(db,str(data.get("request","")))
        return JSONResponse({"id":run.id,"status":run.status,"message":run.error},status_code=202)
    except ValidationError as exc: return JSONResponse({"error":str(exc)},status_code=422)

async def health(request):
    try:
        init_db()
        with db_session() as db: db.query(Task).limit(1).all()
        return JSONResponse({"status":"ok","version":__version__,"database":"ok","model_runtime":"not_configured"})
    except Exception: return JSONResponse({"status":"degraded","database":"error"},status_code=503)

async def stylesheet(request):
    from pathlib import Path
    css=Path(__file__).parent/"web"/"static"/"app.css"
    if not css.exists(): return PlainTextResponse("Stylesheet missing",status_code=404)
    return PlainTextResponse(css.read_text(encoding="utf-8"),media_type="text/css")

def validate_bind_host(host: str) -> str:
    """Reject remote listeners until authentication and CSRF controls exist."""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Remote binding is disabled until authentication, CSRF protection, and authorization are implemented.")
    return host


# Authentication endpoints. Initial setup is available only while no user exists.
import secrets as _secrets
import hmac
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from .security.auth import hash_password, verify_password, create_session, validate_session, revoke_session

async def setup_page(request):
    with db_session() as db:
        if db.query(__import__("lifeops.storage.models", fromlist=["User"]).User).count():
            return page("Setup unavailable", '<section class="panel"><h2>Setup is already complete</h2><a href="/login">Sign in</a></section>')
    body='<section class="panel"><h2>Create local administrator</h2><p>This one-time setup is available only before the first account exists.</p><form class="task-form" method="post" action="/setup"><label>Username<input name="username" required minlength="3" maxlength="64" autocomplete="username"></label><label>Password<input type="password" name="password" required minlength="12" maxlength="1024" autocomplete="new-password"></label><label>Confirm password<input type="password" name="confirm_password" required minlength="12" maxlength="1024" autocomplete="new-password"></label><button class="button">Create administrator</button></form></section>'
    return page("Initial setup",body)

async def setup_submit(request):
    from .storage.models import User
    form=await request.form()
    username=str(form.get("username","")).strip()
    password=str(form.get("password",""))
    if len(username)<3 or len(username)>64 or not username.replace("_","").replace("-","").isalnum():
        return page("Initial setup",'<section class="panel"><p class="error">Username must be 3–64 letters, numbers, underscores, or hyphens.</p><a href="/setup">Try again</a></section>')
    if password != str(form.get("confirm_password","")):
        return page("Initial setup",'<section class="panel"><p class="error">Passwords do not match.</p><a href="/setup">Try again</a></section>')
    try: encoded=hash_password(password).encoded
    except ValueError as exc: return page("Initial setup",f'<section class="panel"><p class="error">{escape(str(exc))}</p><a href="/setup">Try again</a></section>')
    with db_session() as db:
        if db.query(User).count():
            return page("Setup unavailable",'<section class="panel"><p>Setup already completed.</p><a href="/login">Sign in</a></section>')
        user=User(username=username,password_hash=encoded,role="admin")
        db.add(user); db.commit(); db.refresh(user)
        session_obj=create_session(db,user.id)
    response=RedirectResponse("/",status_code=303)
    response.set_cookie("lifeops_session",getattr(session_obj,"_raw_token",session_obj.id),max_age=43200,httponly=True,secure=request.url.scheme=="https",samesite="lax",path="/")
    response.set_cookie("lifeops_csrf",_secrets.token_urlsafe(32),max_age=43200,httponly=False,secure=request.url.scheme=="https",samesite="lax",path="/")
    return response

async def login_page(request):
    body='<section class="panel"><h2>Sign in</h2><form class="task-form" method="post" action="/login"><label>Username<input name="username" required autocomplete="username"></label><label>Password<input type="password" name="password" required autocomplete="current-password"></label><button class="button">Sign in</button></form></section>'
    return page("Sign in",body)

async def login_submit(request):
    from .storage.models import User
    form=await request.form()
    username=str(form.get("username","")).strip()
    password=str(form.get("password",""))
    with db_session() as db:
        user=db.query(User).filter_by(username=username).first()
        if not user or not verify_password(password,user.password_hash):
            return page("Sign in",'<section class="panel"><p class="error">Invalid username or password.</p><a href="/login">Try again</a></section>')
        session_obj=create_session(db,user.id)
    response=RedirectResponse("/",status_code=303)
    response.set_cookie("lifeops_session",getattr(session_obj,"_raw_token",session_obj.id),max_age=43200,httponly=True,secure=request.url.scheme=="https",samesite="lax",path="/")
    response.set_cookie("lifeops_csrf",_secrets.token_urlsafe(32),max_age=43200,httponly=False,secure=request.url.scheme=="https",samesite="lax",path="/")
    return response

async def logout_route(request):
    sid=request.cookies.get("lifeops_session","")
    with db_session() as db: revoke_session(db,sid)
    response=RedirectResponse("/login",status_code=303)
    response.delete_cookie("lifeops_session",path="/")
    response.delete_cookie("lifeops_csrf",path="/")
    return response

class LocalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path=request.url.path
        if path in {"/setup","/login","/health","/static/app.css"}:
            return await call_next(request)
        with db_session() as db:
            from .storage.models import User
            has_users=db.query(User).count()>0
            user=validate_session(db,request.cookies.get("lifeops_session","")) if has_users else None
        if not has_users:
            return RedirectResponse("/setup",status_code=303) if not path.startswith("/api/") else JSONResponse({"error":"initial_setup_required"},status_code=401)
        if user is None:
            return RedirectResponse("/login",status_code=303) if not path.startswith("/api/") else JSONResponse({"error":"authentication_required"},status_code=401)
        request.state.user_id=user.id
        if request.method not in {"GET","HEAD","OPTIONS"}:
            cookie_token=request.cookies.get("lifeops_csrf","")
            supplied=request.headers.get("x-csrf-token","")
            if not supplied:
                try:
                    form=await request.form()
                    supplied=str(form.get("_csrf",""))
                except Exception:
                    supplied=""
            # Same-origin validation protects ordinary HTML forms; token matching
            # is additionally required when a browser client supplies the token.
            origin=request.headers.get("origin","")
            expected_origin=str(request.base_url).rstrip("/")
            if supplied:
                valid=bool(cookie_token and hmac.compare_digest(cookie_token,supplied))
            else:
                valid=bool(origin and hmac.compare_digest(origin.rstrip("/"),expected_origin))
            if not valid:
                return JSONResponse({"error":"csrf_validation_failed"},status_code=403)
        return await call_next(request)

routes=[Route("/setup",setup_page,methods=["GET"]),Route("/setup",setup_submit,methods=["POST"]),Route("/login",login_page,methods=["GET"]),Route("/login",login_submit,methods=["POST"]),Route("/logout",logout_route,methods=["POST"]),Route("/",home),Route("/tasks",tasks_page,methods=["GET"]),Route("/tasks",create_task_route,methods=["POST"]),Route("/tasks/{task_id:int}/complete",complete_task_route,methods=["POST"]),Route("/notes",notes_page,methods=["GET"]),Route("/notes",create_note_route,methods=["POST"]),Route("/projects",projects_page),Route("/projects",create_project_route,methods=["POST"]),Route("/memory",memory_page),Route("/memory",create_memory_route,methods=["POST"]),Route("/memory/{memory_id:int}/delete",delete_memory_route,methods=["POST"]),Route("/approvals",approvals_page),Route("/approvals/{approval_id:int}/decision",approval_decision_route,methods=["POST"]),Route("/api/v1/tasks",api_tasks,methods=["GET","POST"]),Route("/api/v1/memories",api_memories,methods=["GET","POST"]),Route("/api/v1/approvals",api_approvals,methods=["GET","POST"]),Route("/api/v1/approvals/{approval_id:int}/decision",api_approval_decision,methods=["POST"]),Route("/api/v1/agent-runs",api_agent_runs,methods=["POST"]),Route("/selfx",selfx_page),Route("/selfx/goals",create_goal_route,methods=["POST"]),Route("/selfx/proposals",create_proposal_route,methods=["POST"]),Route("/selfx/proposals/{proposal_id:int}/decision",proposal_decision_route,methods=["POST"]),Route("/settings",settings_page),Route("/settings/model",save_model_settings,methods=["POST"]),Route("/health",health),Route("/static/app.css",stylesheet)]
app=FastHTML(routes=routes,lifespan=lifespan)
app.add_middleware(LocalAuthMiddleware)
if __name__=="__main__":
    try:
        host=validate_bind_host(os.getenv("LIFEOPS_HOST","127.0.0.1"))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    uvicorn.run(app,host=host,port=int(os.getenv("LIFEOPS_PORT","5001")))
