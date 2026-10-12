"""FastHTML page renderers for all 20 LifeOps sections (data-driven)."""
import datetime

from fasthtml.common import *

from lifeops.web.layout import page_layout, status_badge, stat_card

from fasthtml.common import ft
def code(*c, **kw):
    return ft('code', *c, **kw)




def _fmt(dt):
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    if isinstance(dt, datetime.date):
        return dt.strftime("%Y-%m-%d")
    return str(dt) if dt is not None else "-"


def _table(headers, rows, empty_msg="Nothing here yet."):
    if not rows:
        return P(empty_msg, cls="muted")
    return Table(
        Thead(Tr(*[Th(h) for h in headers])),
        Tbody(*rows), cls="data-table")


def _form(action, fields, submit="Save"):
    inputs = []
    for f in fields:
        name, ftype = f["name"], f.get("type", "text")
        if ftype == "textarea":
            inputs.append(Textarea(f.get("value", ""), name=name,
                                   placeholder=f.get("ph", name),
                                   required=f.get("required", False)))
        elif ftype == "select":
            inputs.append(Select(*[Option(o, value=o, selected=(o == f.get("value")))
                                   for o in f["options"]], name=name))
        elif ftype == "hidden":
            inputs.append(Input(type="hidden", name=name, value=f.get("value", "")))
        else:
            inputs.append(Input(type=ftype, name=name, placeholder=f.get("ph", name),
                                value=f.get("value", ""),
                                required=f.get("required", False)))
    inputs.append(Button(submit, cls="btn", type="submit"))
    return Form(*inputs, action=action, method="post", cls="inline-form")

# --------------------------------------------------------------------------- pages

def render_dashboard(d=None):
    d = d or {}
    stats = Div(
        stat_card("Open Tasks", d.get("tasks_open", "-"), "stat-tasks"),
        stat_card("Active Agent Runs", d.get("agent_runs_active", "-"), "stat-runs"),
        stat_card("Pending Approvals", d.get("pending_approvals", "-"), "stat-approvals"),
        stat_card("Memories", d.get("memories", "-"), "stat-memories"),
        stat_card("Self-X Health", d.get("selfx_health", "-"), "stat-health"),
        stat_card("Backups", d.get("backups", "-"), "stat-backups"),
        id="dashboard-stats", cls="stat-grid")
    recent_rows = [Tr(Td(t.title), Td(status_badge(t.status.value)), Td(t.priority),
                      Td(_fmt(t.created_at)))
                   for t in d.get("recent_tasks", [])]
    body = Div(
        H2("Control Center"),
        stats,
        Div(H3("Recent Tasks"),
            _table(["Title", "Status", "Priority", "Created"], recent_rows), cls="card"),
        Div(H3("Quick Actions"),
            A("Create Task", href="/tasks", cls="btn"), " ",
            A("Ask Assistant", href="/assistant", cls="btn btn-secondary"), " ",
            A("Run Backup", href="/backups", cls="btn btn-secondary"), cls="card"),
    )
    if d.get("emergency_active"):
        body = Div(Div("EMERGENCY STOP ACTIVE - all mutating operations are blocked.",
                       cls="stop-banner"), body)
    return page_layout("Dashboard", "dashboard", body)


def render_tasks_page(tasks=None, projects=None, flash=None):
    tasks = tasks or []
    rows = []
    for t in tasks:
        done = t.status.value == "SUCCEEDED"
        action = (Span("Done", cls="badge badge-success") if done else
                  Form(Input(type="hidden", name="task_id", value=str(t.id)),
                       Button("Complete", cls="btn btn-sm", type="submit"),
                       action="/tasks/complete", method="post"))
        del_form = (Form(Input(type="hidden", name="task_id", value=str(t.id)),
                         Button("X", cls="btn btn-sm btn-danger", type="submit"),
                         action="/tasks/delete", method="post")
                    if not done else "")
        rows.append(Tr(Td(str(t.id)), Td(t.title), Td(status_badge(t.status.value)),
                       Td(t.priority), Td(_fmt(t.due_date)), Td(action), Td(del_form)))
    proj_names = [p.name for p in (projects or [])]
    form_fields = [
        {"name": "title", "ph": "Task title", "required": True},
        {"name": "priority", "type": "select", "options": ["high", "medium", "low"]},
        {"name": "due_date", "type": "date"},
        {"name": "project", "type": "select", "options": [""] + proj_names},
    ]
    body = Div(
        Div(H3("Create Task"), _form("/tasks/create", form_fields, "Add Task"), cls="card"),
        Div(H3("Tasks"),
            _table(["ID", "Title", "Status", "Priority", "Due", "", ""], rows), cls="card"))
    return page_layout("Tasks & Projects", "tasks", body, flash=flash)


def render_assistant_page(messages=None, conversations=None, error=None):
    bubbles = []
    for m in messages or []:
        cls = "chat-user" if m.role == "user" else "chat-assistant"
        bubbles.append(Div(Strong(m.role.capitalize() + ": "), Span(m.content),
                           cls="chat-msg " + cls))
    conv_links = [Li(A("Conversation " + str(c.id) + " (" + _fmt(c.created_at) + ")",
                       href="/assistant?conversation=" + str(c.id)))
                  for c in (conversations or [])][-10:]
    body = Div(
        Div(H3("Chat"),
            Div(*bubbles, cls="chat-history", id="chat-history"),
            Form(Input(type="text", name="prompt",
                       placeholder="Ask LifeOps anything...",
                       required=True, style="flex:1;min-width:250px;"),
                 Input(type="hidden", name="conversation",
                       value=str(conversations[-1].id if conversations else "")),
                 Button("Send", cls="btn", type="submit"),
                 action="/assistant/message", method="post", cls="inline-form"),
            cls="card"),
        Div(H3("Conversations"),
            Ul(*conv_links) if conv_links else P("No conversations yet.", cls="muted"),
            cls="card"),
    )
    return page_layout("AI Assistant", "assistant", body, error=error)


def render_calendar_page(events=None, conflicts=None, flash=None):
    rows = [Tr(Td(e.title), Td(_fmt(e.start_time)), Td(_fmt(e.end_time)), Td(e.time_zone),
               Td("Yes" if e.is_recurring else "-"))
            for e in (events or [])]
    conflict_items = [Li(str(c.get("title", "?")) + " overlaps " + str(c.get("with_title", "?")),
                        cls="muted") for c in (conflicts or [])]
    body = Div(
        Div(H3("Add Event"), _form("/calendar/create", [
            {"name": "title", "ph": "Event title", "required": True},
            {"name": "start_time", "type": "datetime-local", "required": True},
            {"name": "end_time", "type": "datetime-local", "required": True},
        ], "Schedule"), cls="card"),
        Div(H3("Upcoming Events"),
            _table(["Title", "Start", "End", "TZ", "Recurring"], rows), cls="card"),
        Div(H3("Conflicts"), Ul(*conflict_items) if conflict_items else
            P("No scheduling conflicts detected.", cls="muted"), cls="card"),
    )
    return page_layout("Calendar & Routines", "calendar", body, flash=flash)


def render_notes_page(notes=None, graph=None, q=None, flash=None):
    rows = [Tr(Td(str(n.id)),
               Td(A(n.title, href="/notes/" + str(n.id))),
               Td(", ".join(n.tags or [])), Td(_fmt(n.updated_at)),
               Td(Form(Input(type="hidden", name="note_id", value=str(n.id)),
                       Button("Delete", cls="btn btn-sm btn-danger", type="submit"),
                       action="/notes/delete", method="post")))
            for n in (notes or [])]
    links = []
    if graph:
        for node in graph.get("nodes", [])[:20]:
            deps = graph.get("edges_by_node", {}).get(node, [])
            links.append(Li(Strong(node), ": ",
                            ", ".join(deps) if deps else "(no backlinks)", cls="muted"))
    body = Div(
        Div(H3("New Note"), _form("/notes/create", [
            {"name": "title", "ph": "Note title", "required": True},
            {"name": "content", "type": "textarea",
             "ph": "Markdown content. Link notes with [[Another Note]]."},
            {"name": "tags", "ph": "comma,separated,tags"},
        ], "Create"), cls="card"),
        Form(Input(type="text", name="q", value=q or "", placeholder="Search notes..."),
             Button("Search", cls="btn btn-secondary", type="submit"),
             action="/notes", method="get", cls="inline-form"),
        Div(H3("Notes"), _table(["ID", "Title", "Tags", "Updated", ""], rows), cls="card"),
        Div(H3("Knowledge Graph"),
            Ul(*links) if links else
            P("Create notes with [[wikilinks]] to build the graph.", cls="muted"), cls="card"),
    )
    return page_layout("Notes & Knowledge", "notes", body, flash=flash)


def render_note_detail(note=None, flash=None):
    backlinks = [A(b, href="/notes?q=" + b) for b in (note.backlinks or [])] if note else []
    parts = []
    if note:
        parts.append(Div(H3(note.title),
                         Pre(note.content, style="white-space:pre-wrap"),
                         P("Backlinks from: ", *backlinks) if backlinks else "",
                         cls="card"))
    else:
        parts.append(P("Note not found.", cls="muted"))
    parts.append(Div(H3("Edit"), _form("/notes/update", [
        {"name": "note_id", "type": "hidden", "value": str(note.id) if note else ""},
        {"name": "title", "value": note.title if note else ""},
        {"name": "content", "type": "textarea", "value": note.content if note else ""},
    ], "Update"), cls="card"))
    parts.append(A("Back to notes", href="/notes", cls="btn btn-secondary"))
    return page_layout("Notes & Knowledge", "notes", Div(*parts), flash=flash)


def render_memory_page(memories=None, revisions=None, q=None, flash=None):
    rows = [Tr(Td(str(m.id)), Td(m.category), Td(m.key),
               Td((m.value[:80] + "...") if len(m.value) > 80 else m.value),
               Td("%.2f" % m.confidence), Td("Stale" if m.is_stale else "Fresh"),
               Td(Form(Input(type="hidden", name="memory_id", value=str(m.id)),
                       Button("Delete", cls="btn btn-sm btn-danger", type="submit"),
                       action="/memory/delete", method="post")))
            for m in (memories or [])]
    rev_rows = [Tr(Td(str(r.memory_id)), Td(r.old_value[:60]), Td(r.new_value[:60]),
                   Td(_fmt(r.revised_at))) for r in (revisions or [])]
    body = Div(
        Div(H3("Store Memory"), _form("/memory/store", [
            {"name": "category", "type": "select",
             "options": ["profile", "preference", "fact", "pattern", "goal_context"]},
            {"name": "key", "ph": "key", "required": True},
            {"name": "value", "type": "textarea", "ph": "What should the agent remember?"},
        ], "Remember"), cls="card"),
        Form(Input(type="text", name="q", value=q or "", placeholder="Search memory..."),
             Button("Search", cls="btn btn-secondary", type="submit"),
             action="/memory", method="get", cls="inline-form"),
        Div(H3("Memories"),
            _table(["ID", "Category", "Key", "Value", "Conf", "State", ""], rows), cls="card"),
        Div(H3("Revision History"), _table(["Memory", "Old", "New", "When"], rev_rows),
            cls="card"),
    )
    return page_layout("Memory Explorer", "memory", body, flash=flash)


def render_files_page(documents=None, results=None, q=None, flash=None):
    rows = [Tr(Td(str(d.id)), Td(d.filename), Td(d.indexing_status),
               Td(str(d.file_size) + " B"), Td(_fmt(d.indexed_at)),
               Td(Form(Input(type="hidden", name="document_id", value=str(d.id)),
                       Button("Remove", cls="btn btn-sm btn-danger", type="submit"),
                       action="/files/delete", method="post")))
            for d in (documents or [])]
    res_items = [Li(Span(str(r.get("snippet", ""))), " - ", code(str(r.get("filepath", ""))),
                    cls="muted") for r in (results or [])]
    body = Div(
        Div(H3("Index a Directory"), _form("/files/index", [
            {"name": "directory", "ph": "/path/to/documents", "required": True},
        ], "Index"), cls="card"),
        Form(Input(type="text", name="q", value=q or "", placeholder="Full-text search..."),
             Button("Search", cls="btn btn-secondary", type="submit"),
             action="/files", method="get", cls="inline-form"),
        Div(H3("Search Results"), Ul(*res_items) if res_items else
            P("Run a search above.", cls="muted"), cls="card"),
        Div(H3("Indexed Documents"),
            _table(["ID", "File", "Status", "Size", "Indexed", ""], rows), cls="card"),
    )
    return page_layout("Files & Documents", "files", body, flash=flash)


def render_search_page(q=None, results=None):
    blocks = []
    for section, items in (results or {}).items():
        lis = [Li(str(i.get("title") or i.get("key") or i.get("filename") or i)[:120])
               for i in items[:10]]
        blocks.append(Div(H3(section.replace("_", " ").title()),
                          Ul(*lis) if lis else P("No matches.", cls="muted"), cls="card"))
    body = Div(
        Form(Input(type="text", name="q", value=q or "", placeholder="Search everything..."),
             Button("Search", cls="btn", type="submit"),
             action="/search", method="get", cls="inline-form"),
        *(blocks if q else [P("Type a query to search tasks, notes, memories and documents.",
                              cls="muted")]))
    return page_layout("Unified Search", "notes", body)


def render_workflows_page(workflows=None, runs=None, flash=None, error=None):
    rows = []
    for w in workflows or []:
        acts = []
        if w.status in ("draft", "paused", "disabled"):
            acts.append(("Activate", "/workflows/" + str(w.id) + "/activate"))
        if w.status == "active":
            acts.append(("Pause", "/workflows/" + str(w.id) + "/pause"))
            acts.append(("Run", "/workflows/" + str(w.id) + "/run"))
        acts.append(("Duplicate", "/workflows/" + str(w.id) + "/duplicate"))
        acts.append(("Delete", "/workflows/" + str(w.id) + "/delete"))
        rows.append(Tr(Td(w.name), Td("v" + str(w.version)), Td(status_badge(w.status)),
                       Td(str(len((w.definition_json or {}).get("steps", [])))),
                       Td(*[Form(Input(type="hidden", name="workflow_id", value=str(w.id)),
                                  Button(a, cls="btn btn-sm btn-secondary", type="submit"),
                                  action=p, method="post") for a, p in acts])))
    run_rows = [Tr(Td(r.workflow_id), Td(status_badge(r.status)), Td(_fmt(r.started_at)),
                   Td(_fmt(r.finished_at)),
                   Td(str((r.result_json or {}).get("summary", ""))[:80]))
                for r in (runs or [])]
    body = Div(
        Div(H3("New Workflow (JSON definition)"),
            Form(Textarea(name="definition",
                          placeholder='{"name":"My flow","steps":[{"id":"s1","tool":"noop","args":{}}]}',
                          rows=6),
                 Button("Create", cls="btn", type="submit"),
                 action="/workflows/create", method="post", cls="inline-form"),
            P("Steps support depends_on, retry, timeout_seconds and requires_approval. "
              "Cycles are rejected.", cls="muted"), cls="card"),
        Div(H3("Workflows"), _table(["Name", "Version", "Status", "Steps", "Actions"], rows),
            cls="card"),
        Div(H3("Recent Runs"),
            _table(["Workflow", "Status", "Started", "Finished", "Summary"], run_rows),
            cls="card"),
    )
    return page_layout("Automation & Scheduler", "workflows", body, flash=flash, error=error)


def render_workers_page(jobs=None, events=None, stats=None, flash=None):
    job_rows = []
    for j in jobs or []:
        job_rows.append(Tr(Td(j.name), Td(code(j.cron_expression)),
                           Td(status_badge("ACTIVE" if j.enabled else "DISABLED")),
                           Td(_fmt(j.last_run_at)),
                           Td(Form(Input(type="hidden", name="job_id", value=str(j.id)),
                                   Button("Run Now", cls="btn btn-sm", type="submit"),
                                   action="/workers/run-now", method="post"),
                              Form(Input(type="hidden", name="job_id", value=str(j.id)),
                                   Button("Toggle", cls="btn btn-sm btn-secondary",
                                          type="submit"),
                                   action="/workers/toggle", method="post"))))
    ev_rows = [Tr(Td(e.job_id), Td(e.event_type), Td(str(e.details)[:90]), Td(_fmt(e.timestamp)))
               for e in (events or [])]
    st = stats or {}
    body = Div(
        Div(Div(Span(str(st.get("queued", 0)), cls="value"), Span("Queued", cls="label"),
                cls="stat-card"),
            Div(Span(str(st.get("running", 0)), cls="value"), Span("Running", cls="label"),
                cls="stat-card"),
            Div(Span(str(st.get("completed", 0)), cls="value"), Span("Completed", cls="label"),
                cls="stat-card"),
            Div(Span(str(st.get("failed", 0)), cls="value"), Span("Failed", cls="label"),
                cls="stat-card"),
            cls="stat-grid"),
        Div(H3("New Scheduled Job"), _form("/workers/create-job", [
            {"name": "name", "ph": "Job name", "required": True},
            {"name": "cron", "ph": "0 7 * * *", "required": True},
            {"name": "handler", "type": "select",
             "options": ["noop", "create_task", "daily_plan"]},
            {"name": "payload", "ph": '{"title":"Morning review"}'},
        ], "Schedule"), cls="card"),
        Div(H3("Jobs"), _table(["Name", "Cron", "State", "Last Run", "Actions"], job_rows),
            cls="card"),
        Div(H3("Job Events"), _table(["Job", "Event", "Details", "Time"], ev_rows), cls="card"),
    )
    return page_layout("Worker Monitor", "workers", body, flash=flash)


def render_tools_page(tools=None, integrations=None, policy=None, flash=None, error=None):
    tool_rows = [Tr(Td(t["name"]), Td(str(t.get("description", ""))[:80]),
                    Td(status_badge(str(t.get("risk_level", "low")).upper())),
                    Td(str(t.get("permissions", []))[:60]))
                 for t in (tools or [])]
    int_rows = []
    for i in integrations or []:
        int_rows.append(Tr(Td(i.name), Td(i.health_status),
                           Td(status_badge("ENABLED" if i.enabled else "DISABLED")),
                           Td(Form(Input(type="hidden", name="integration_id", value=str(i.id)),
                                   Button("Toggle", cls="btn btn-sm", type="submit"),
                                   action="/tools/integration-toggle", method="post"))))
    pol_rows = [Tr(Td(p["action"]), Td(status_badge(p["effect"])), Td(p.get("reason", "")))
                for p in (policy or [])]
    body = Div(
        Div(H3("Registered Tools"),
            _table(["Tool", "Description", "Risk", "Permissions"], tool_rows), cls="card"),
        Div(H3("Integrations"), _form("/tools/integration-add", [
            {"name": "name", "ph": "Integration name", "required": True},
            {"name": "config", "ph": '{"url":"..."} JSON optional'},
        ], "Register"), _table(["Name", "Health", "State", ""], int_rows), cls="card"),
        Div(H3("Policy Rules"), _table(["Action", "Effect", "Reason"], pol_rows), cls="card"),
    )
    return page_layout("Tools & Integrations", "tools", body, flash=flash, error=error)


def render_models_page(runtime=None, models=None, test_result=None, flash=None):
    rt = runtime or {}
    body = Div(
        Div(H3("Runtime Detection"),
            P("LiteRT-LM binary: ", code(str(rt.get("litert_lm_binary", "not found"))), Br(),
              "Detected models: ", code(", ".join(rt.get("models", [])) or "none"), Br(),
              "Adapter in use: ", code(str(rt.get("adapter", "mock")))), cls="card"),
        Div(H3("Test Prompt"),
            Form(Input(type="text", name="prompt", placeholder="Say hello...", required=True),
                 Button("Run", cls="btn", type="submit"),
                 action="/models/test", method="post", cls="inline-form"),
            (Pre(str(test_result), style="white-space:pre-wrap") if test_result else ""),
            cls="card"),
        Div(H3("Model Settings"),
            Form(Input(type="hidden", name="section", value="model.default"),
                 Input(type="text", name="model_name", placeholder="model.gguf name"),
                 Input(type="number", name="context_length", placeholder="4096"),
                 Input(type="number", name="temperature", step="0.1", placeholder="0.7"),
                 Button("Save", cls="btn", type="submit"),
                 action="/models/settings", method="post", cls="inline-form"),
            P("Stored under settings section model.default.", cls="muted"), cls="card"),
    )
    return page_layout("Model Manager", "models", body, flash=flash)


def render_security_page(approvals=None, audit=None, stop=None, policy=None, flash=None):
    rows = []
    for a in approvals or []:
        pending = a.decision.value == "PENDING"
        approve_btn = (Form(Input(type="hidden", name="approval_id", value=str(a.id)),
                            Input(type="hidden", name="decision", value="APPROVED"),
                            Button("Approve", cls="btn btn-sm", type="submit"),
                            action="/security/approve", method="post") if pending else "")
        reject_btn = (Form(Input(type="hidden", name="approval_id", value=str(a.id)),
                           Input(type="hidden", name="decision", value="REJECTED"),
                           Button("Reject", cls="btn btn-sm btn-danger", type="submit"),
                           action="/security/approve", method="post") if pending else "")
        rows.append(Tr(Td(a.action_type), Td(a.description[:100]), Td(str(a.agent_run_id)),
                       Td(status_badge(a.decision.value)), Td(approve_btn), Td(reject_btn)))
    audit_rows = [Tr(Td(_fmt(ev.timestamp)), Td(ev.actor), Td(ev.action), Td(ev.target or ""),
                     Td(status_badge(str(ev.outcome).upper()))) for ev in (audit or [])]
    stop_state = stop or {}
    if stop_state.get("active"):
        stop_ui = (Div("EMERGENCY STOP IS ACTIVE: " + str(stop_state.get("reason", "")),
                       cls="stop-banner"),
                   Form(Button("Release Emergency Stop", cls="btn", type="submit"),
                        action="/security/emergency-release", method="post"))
    else:
        stop_ui = Form(Input(type="text", name="reason", placeholder="reason (optional)"),
                       Button("ENGAGE EMERGENCY STOP", cls="btn btn-danger", type="submit"),
                       action="/security/emergency-stop", method="post", cls="inline-form")
    body = Div(
        Div(H3("Kill Switch"), stop_ui, cls="card"),
        Div(H3("Approval Requests"),
            _table(["Action", "Description", "Run", "Decision", "", ""], rows), cls="card"),
        Div(H3("Audit Trail (last 50)"),
            _table(["Time", "Actor", "Action", "Target", "Outcome"], audit_rows), cls="card"),
    )
    return page_layout("Security & Approvals", "security", body, flash=flash)


def render_selfx_page(identity=None, diagnostics=None, goals=None, evaluations=None,
                      improvements=None, checkpoints=None, flash=None):
    goal_rows = [Tr(Td(str(g.objective)[:80]), Td(status_badge(str(g.status).upper())),
                    Td(str(g.target)[:60]), Td(_fmt(g.created_at))) for g in (goals or [])]
    eval_rows = [Tr(Td(e.suite_name), Td("%.1f" % e.score), Td(_fmt(e.created_at)))
                 for e in (evaluations or [])]
    imp_rows = [Tr(Td(str(p.problem)[:80]), Td(status_badge(str(p.risk_level).upper())),
                  Td(status_badge(str(p.status).upper())), Td(_fmt(p.created_at)))
                for p in (improvements or [])]
    cp_rows = [Tr(Td(c.id), Td(str(c.description)[:80]), Td(_fmt(c.created_at)))
               for c in (checkpoints or [])]
    diag = diagnostics or {}
    body = Div(
        Div(H3("Identity"), Pre(str(identity), style="white-space:pre-wrap"), cls="card"),
        Div(H3("Diagnostics"),
            P("Health: ", status_badge(str(diag.get("status", "unknown")).upper()), " ",
              str(diag.get("message", "")), Br(),
              Form(Button("Run Self-Diagnosis", cls="btn", type="submit"),
                   action="/selfx/diagnose", method="post"), cls="inline-form"), cls="card"),
        Div(H3("Improvement Goals"), _form("/selfx/goal", [
            {"name": "objective", "ph": "What should improve?", "required": True},
            {"name": "target", "ph": '{"metric":"success_rate","value":0.9}'},
        ], "Add Goal"), _table(["Objective", "Status", "Target", "Created"], goal_rows),
            cls="card"),
        Div(H3("Evaluations"), _table(["Suite", "Score", "When"], eval_rows), cls="card"),
        Div(H3("Improvement Proposals"),
            _table(["Problem", "Risk", "Status", "Created"], imp_rows), cls="card"),
        Div(H3("Checkpoints"), _form("/selfx/checkpoint", [
            {"name": "description", "ph": "Checkpoint description", "required": True}],
            "Snapshot"),
            _table(["ID", "Description", "Created"], cp_rows), cls="card"),
    )
    return page_layout("Self-X Control Center", "selfx", body, flash=flash)


def render_skills_page(skills=None, tests=None, flash=None, error=None):
    rows = []
    for s in skills or []:
        actions = [Form(Input(type="hidden", name="skill_id", value=str(s.id)),
                        Button("Publish", cls="btn btn-sm", type="submit"),
                        action="/skills/publish", method="post")]
        actions.append(Form(Input(type="hidden", name="skill_id", value=str(s.id)),
                            Button("Disable" if s.enabled else "Enable",
                                   cls="btn btn-sm btn-secondary", type="submit"),
                            action="/skills/toggle", method="post"))
        rows.append(Tr(Td(s.name), Td(s.id), Td("v" + str(s.current_version)),
                       Td(status_badge("ENABLED" if s.enabled else "DISABLED")), Td(*actions)))
    test_rows = [Tr(Td(t.skill_id), Td(t.test_name),
                    Td(status_badge("PASSED" if t.last_passed else
                                    ("FAILED" if t.last_passed is False else "UNRUNNED"))),
                  Td(_fmt(t.last_run_at)),
                  Td(Form(Input(type="hidden", name="test_id", value=str(t.id)),
                          Button("Run", cls="btn btn-sm", type="submit"),
                          action="/skills/test/run", method="post")))
                 for t in (tests or [])]
    body = Div(
        Div(H3("Author Skill"), _form("/skills/create", [
            {"name": "name", "ph": "Skill name", "required": True},
            {"name": "description", "type": "textarea", "ph": "What does this skill do?"},
            {"name": "instructions", "type": "textarea",
             "ph": "Step-by-step instructions (the skill body)"},
        ], "Draft Skill"),
            P("Publishing is gated: all attached tests must pass first.", cls="muted"),
            cls="card"),
        Div(H3("Add Test"), _form("/skills/test/add", [
            {"name": "skill_id", "ph": "skill id", "required": True},
            {"name": "test_name", "ph": "Test name", "required": True},
            {"name": "test_input", "ph": '{"in": ...}'},
            {"name": "expected_output", "ph": '{"out": ...}'},
        ], "Add Test"), cls="card"),
        Div(H3("Skills"), _table(["Name", "ID", "Version", "State", "Actions"], rows),
            cls="card"),
        Div(H3("Tests"), _table(["Skill", "Test", "Result", "Last Run", ""], test_rows),
            cls="card"),
    )
    return page_layout("Skills Studio", "skills", body, flash=flash, error=error)


def render_research_page(jobs=None, sources=None, flash=None):
    rows = [Tr(Td(j.topic), Td(status_badge(str(j.status).upper())), Td(_fmt(j.created_at)),
             Td(str((j.findings or {}).get("summary", ""))[:100]))
            for j in (jobs or [])]
    src_rows = [Tr(Td(s.url), Td(s.title or ""),
                   Td(status_badge("VERIFIED" if s.verified_flag else "UNVERIFIED")),
                   Td(s.citation or "")) for s in (sources or [])]
    body = Div(
        Div(H3("New Research Job"), _form("/research/create", [
            {"name": "topic", "ph": "Research topic", "required": True},
        ], "Research"),
            P("Network access follows policy: when disabled, research runs local-only "
              "against indexed documents and notes.", cls="muted"), cls="card"),
        Div(H3("Jobs"), _table(["Topic", "Status", "Created", "Findings"], rows), cls="card"),
        Div(H3("Sources & Citations"),
            _table(["URL", "Title", "Verified", "Citation"], src_rows), cls="card"),
    )
    return page_layout("Research Center", "research", body, flash=flash)


def render_analytics_page(summary=None, evaluations=None, flash=None):
    s = summary or {}
    rate = s.get("task_success_rate", 0)
    avg = s.get("avg_eval_score", 0)
    body = Div(
        Div(stat_card("Total Tasks", s.get("tasks_total", "-")),
            stat_card("Success Rate",
                      "%.0f%%" % (rate * 100) if isinstance(rate, (int, float)) else "-"),
            stat_card("Agent Runs", s.get("runs_total", "-")),
            stat_card("Avg Eval Score",
                      "%.1f" % avg if isinstance(avg, (int, float)) else "-"),
            stat_card("Tool Calls", s.get("tool_calls_total", "-")),
            stat_card("Jobs Executed", s.get("jobs_executed", "-")),
            cls="stat-grid"),
        Div(H3("Evaluation Trend"),
            _table(["Suite", "Score", "When"],
                   [Tr(Td(e.suite_name), Td("%.1f" % e.score), Td(_fmt(e.created_at)))
                    for e in (evaluations or [])]), cls="card"),
    )
    return page_layout("Analytics & Reports", "analytics", body, flash=flash)


def render_backups_page(backups=None, flash=None, error=None):
    rows = []
    for b in backups or []:
        rows.append(Tr(Td(b.id), Td(_fmt(b.created_at)),
                       Td(status_badge("VERIFIED" if b.verified else "UNVERIFIED")),
                       Td(code(str(b.file_hash)[:16])),
                       Td(Form(Input(type="hidden", name="backup_id", value=str(b.id)),
                               Button("Verify", cls="btn btn-sm", type="submit"),
                               action="/backups/verify", method="post"),
                          Form(Input(type="hidden", name="backup_id", value=str(b.id)),
                               Input(type="hidden", name="confirm", value="true"),
                               Button("Restore", cls="btn btn-sm btn-danger", type="submit"),
                               action="/backups/restore", method="post"))))
    body = Div(
        Div(H3("Create Snapshot"),
            Form(Button("Backup Now", cls="btn", type="submit"),
                 action="/backups/create", method="post", cls="inline-form"),
            Form(Button("Apply Retention Policy", cls="btn btn-secondary", type="submit"),
                 action="/backups/retention", method="post", cls="inline-form"),
            P("Snapshots use SQLite's online backup API, are hashed (SHA-256), "
              "and must verify before restore.", cls="muted"), cls="card"),
        Div(H3("Backup Records"), _table(["ID", "Created", "State", "Hash", "Actions"], rows),
            cls="card"),
    )
    return page_layout("Backup & Recovery", "backups", body, flash=flash, error=error)


def render_notifications_page(notifications=None, flash=None):
    rows = []
    for n in notifications or []:
        rows.append(Tr(Td(_fmt(n.created_at)), Td(status_badge(str(n.level).upper())),
                       Td(n.title), Td(str(n.message)[:120]),
                       Td("" if n.read else
                          Form(Input(type="hidden", name="notification_id", value=str(n.id)),
                               Button("Mark Read", cls="btn btn-sm", type="submit"),
                               action="/notifications/read", method="post"))))
    body = Div(H3("Notifications"), _table(["Time", "Level", "Title", "Message", ""], rows),
               cls="card")
    return page_layout("Notifications", "notifications", body, flash=flash)


SETTINGS_SECTIONS = [
    ("general", {"app_name": "LifeOps AI", "theme": "dark"}),
    ("autonomy.profile", {"profile": "supervised"}),
    ("model.default", {"model_name": "", "context_length": 4096, "temperature": 0.7}),
    ("network", {"enabled": False, "allowed_domains": []}),
    ("filesystem", {"allowed_paths": ["workspace"], "blocked_paths": ["/etc", "/root"]}),
    ("security.auth_enabled", {"auth_enabled": False}),
    ("security.network_binding",
     {"host": "127.0.0.1", "port": 8000, "expose_network": False}),
    ("privacy.telemetry", {"telemetry": False}),
    ("approvals", {"require_for_risky_tools": True}),
    ("backup", {"retention_count": 10, "auto_backup_cron": "0 3 * * *"}),
]


def render_settings_page(settings=None, profiles=None, flash=None, error=None):
    settings = settings or {}
    cards = []
    for section, defaults in SETTINGS_SECTIONS:
        current = settings.get(section, defaults)
        fields = [{"name": "section", "type": "hidden", "value": section}]
        for k, v in current.items():
            if isinstance(v, bool):
                fields.append({"name": k, "type": "select",
                               "options": ["true", "false"],
                               "value": "true" if v else "false"})
            elif isinstance(v, list):
                fields.append({"name": k,
                               "ph": ",".join(map(str, v)) or "comma,separated"})
            else:
                fields.append({"name": k, "value": str(v)})
        cards.append(Div(H4(section), _form("/settings/save", fields, "Update"), cls="card"))
    prof_buttons = []
    for p in (profiles or []):
        prof_buttons.append(
            Form(Input(type="hidden", name="profile", value=p.get("id", "")),
                 Button(p.get("name", "?") + " - " + p.get("description", ""),
                        cls="btn btn-secondary", type="submit"),
                 action="/settings/profile", method="post"))
    body = Div(
        Div(H3("Autonomy Profiles"), *prof_buttons, cls="card"),
        Div(H3("Settings Sections"), *cards),
        Div(H3("Danger Zone"),
            Form(Button("Restore Factory Defaults", cls="btn btn-danger", type="submit"),
                 action="/settings/reset-all", method="post"), cls="card"),
    )
    return page_layout("Settings", "settings", body, flash=flash, error=error)


def render_help_page(version="0.1.0"):
    body = Div(
        Div(H3("About"),
            P("LifeOps AI + Self-X Evolution Engine - a local-first autonomous "
              "productivity system."), cls="card"),
        Div(H3("Modules"),
            Ul(Li("LifeOps: tasks, calendar, notes, memory, documents, notifications."),
               Li("Agents: assistant chat, orchestrated runs, tool execution, approvals."),
               Li("Self-X: identity, diagnostics, goals, evaluations, skills, checkpoints."),
               Li("Automation: DAG workflows, cron scheduler, worker queue."),
               Li("Platform: settings, audit trail, backups, emergency stop."),
               cls="muted"), cls="card"),
        Div(H3("Troubleshooting"),
            Ul(Li("Server won't start: run scripts/doctor.py"),
               Li("Data looks wrong: create a backup, then restore a verified snapshot."),
               Li("Agent stuck: engage Emergency Stop from the Security page."),
               cls="muted"), cls="card"),
        Div(H3("Version " + str(version)),
            P("Docs: docs/architecture.md - Spec: Prompt.md"), cls="card"),
    )
    return page_layout("Help & About", "help", body)


def render_page_generic(title: str, nav_key: str, description: str):
    return page_layout(title, nav_key,
                       Div(H2(title), P(description),
                           Div(P("Module initialized.", cls="muted"), cls="card")))
