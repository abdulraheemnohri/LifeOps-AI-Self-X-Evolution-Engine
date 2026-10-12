"""Browser-first LifeOps application. Binds to loopback by default."""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from html import escape
from fasthtml.common import FastHTML, serve
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route
from . import __version__
from .database import init_db, get_session_factory, Task, AuditEvent
from .services import create_task, list_tasks, complete_task, create_note, list_notes, ValidationError

@asynccontextmanager
async def lifespan(app):
    init_db(); yield

def page(title: str, body: str) -> HTMLResponse:
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark light"><title>{escape(title)} · LifeOps</title><link rel="stylesheet" href="/static/app.css"></head><body><aside class="sidebar"><a class="brand" href="/">◈ LifeOps <span>SELF-X</span></a><nav><a href="/">Overview</a><a href="/tasks">Tasks</a><a href="/notes">Notes & Knowledge</a><a href="/selfx">Self-X Diagnostics</a><a href="/settings">Settings</a></nav><div class="local-tag">● Local-first workspace</div></aside><main><header><div><p class="eyebrow">PERSONAL OPERATING SYSTEM</p><h1>{escape(title)}</h1></div><span class="pill">v{__version__}</span></header>{body}<footer>LifeOps AI + Self-X · Your data stays on this machine by default.</footer></main></body></html>'''
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
    with db_session() as db: task_count=len(list_tasks(db)); note_count=len(list_notes(db)); audit_count=db.query(AuditEvent).count()
    body=f'''<section class="hero compact"><div><p class="eyebrow">SELF-X CONTROL CENTER</p><h2>Observe first. Improve safely.</h2><p>Diagnostics report what this installation can verify today.</p></div><div class="orb">✳</div></section><section class="stats"><article class="stat"><span>Database</span><strong class="healthy">Connected</strong><small>SQLite session succeeded</small></article><article class="stat"><span>Tasks</span><strong>{task_count}</strong><small>Persistent records</small></article><article class="stat"><span>Notes</span><strong>{note_count}</strong><small>Persistent records</small></article><article class="stat"><span>Audit events</span><strong>{audit_count}</strong><small>Service actions recorded</small></article></section><section class="panel"><h2>Capability report</h2><div class="capability"><span>Local task and note services</span><b class="healthy">Available</b></div><div class="capability"><span>Model inference adapter</span><b class="muted">Not configured</b></div><div class="capability"><span>Autonomous tool execution</span><b class="muted">Not implemented in this phase</b></div><div class="capability"><span>Isolated self-repair and rollback</span><b class="muted">Not implemented in this phase</b></div><p class="hint">Self-X must not claim success without evidence. Later phases will add versioned evaluations, approval-gated repair proposals, and recovery checkpoints.</p></section>'''
    return page("Self-X Diagnostics",body)

async def settings_page(request):
    body='''<section class="panel"><p class="eyebrow">CONFIGURATION</p><h2>Local-first defaults</h2><div class="capability"><span>Network binding</span><b>127.0.0.1 (loopback)</b></div><div class="capability"><span>Storage</span><b>SQLite · data/lifeops.db</b></div><div class="capability"><span>Model runtime</span><b class="muted">Not configured</b></div><div class="capability"><span>Telemetry</span><b>Disabled</b></div><p class="hint">Advanced settings and authentication controls are not yet available. Do not expose this development build to an untrusted network.</p></section>'''
    return page("Settings",body)

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

routes=[Route("/",home),Route("/tasks",tasks_page,methods=["GET"]),Route("/tasks",create_task_route,methods=["POST"]),Route("/tasks/{task_id:int}/complete",complete_task_route,methods=["POST"]),Route("/notes",notes_page,methods=["GET"]),Route("/notes",create_note_route,methods=["POST"]),Route("/selfx",selfx_page),Route("/settings",settings_page),Route("/health",health),Route("/static/app.css",stylesheet)]
app=FastHTML(routes=routes,lifespan=lifespan)
if __name__=="__main__":
    host=os.getenv("LIFEOPS_HOST","127.0.0.1")
    if host not in {"127.0.0.1","localhost","::1"} and os.getenv("LIFEOPS_ALLOW_REMOTE","").lower()!="true": raise SystemExit("Remote binding blocked. Set LIFEOPS_ALLOW_REMOTE=true only after configuring authentication and network protections.")
    serve(app,host=host,port=int(os.getenv("LIFEOPS_PORT","5001")))
