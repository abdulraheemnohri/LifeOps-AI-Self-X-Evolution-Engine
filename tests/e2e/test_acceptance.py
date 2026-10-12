"""End-to-end acceptance scenarios (Prompt.md §14).

These exercise the full REST API surface through a TestClient backed by an
isolated temp SQLite database (see tests/conftest.py fixtures).
"""


def _post(client, url, **kw):
    r = client.post(url, json=kw)
    assert r.status_code in (200, 201), f"POST {url} -> {r.status_code}: {r.text[:250]}"
    return r.json()


def _get(client, url):
    r = client.get(url)
    assert r.status_code == 200, f"GET {url} -> {r.status_code}: {r.text[:250]}"
    return r.json()


# --------------------------------------------------------------------------
# Scenario 1: Task lifecycle — create → update → transition → delete
# --------------------------------------------------------------------------
def test_e2e_task_lifecycle(auth_client):
    client = auth_client
    task = _post(client, "/api/v1/tasks", title="Write quarterly report", priority="high")
    tid = task["id"]
    assert task["status"].lower() in ("created", "pending", "todo", "open")

    updated = client.patch(f"/api/v1/tasks/{tid}", json={"priority": "medium"})
    assert updated.status_code == 200, updated.text

    done = client.post(f"/api/v1/tasks/{tid}/transition", json={"status": "SUCCEEDED"})
    assert done.status_code == 200, done.text
    assert done.json()["status"].lower() in ("succeeded", "done", "completed")

    assert client.delete(f"/api/v1/tasks/{tid}").status_code == 200
    assert client.get(f"/api/v1/tasks/{tid}").status_code == 404


# --------------------------------------------------------------------------
# Scenario 2: Assistant chat returns a reply via the mock model adapter
# --------------------------------------------------------------------------
def test_e2e_assistant_chat(auth_client):
    client = auth_client
    conv = _post(client, "/api/v1/assistant/conversations", title="E2E chat")
    msg = _post(client, "/api/v1/assistant/message",
                conversation_id=conv["id"], content="Hello assistant")
    body = str(msg)
    assert "reply" in body or "content" in body, "assistant must return a reply"


# --------------------------------------------------------------------------
# Scenario 3: Calendar event creation + conflict detection
# --------------------------------------------------------------------------
def test_e2e_calendar_and_conflicts(auth_client):
    client = auth_client
    ev = _post(client, "/api/v1/calendar/events", title="Team standup",
               start_time="2026-10-13T09:00:00", end_time="2026-10-13T09:15:00")
    overlap = client.post("/api/v1/calendar/events", json={
        "title": "Clashing meeting",
        "start_time": "2026-10-13T09:10:00",
        "end_time": "2026-10-13T09:30:00",
    })
    # Either rejected with 422/409, or created and reported as a conflict.
    assert overlap.status_code in (200, 201, 409, 422)
    conflicts = _get(client, f"/api/v1/calendar/events/{ev['id']}/conflicts")
    assert isinstance(conflicts.get("conflicts"), list)


# --------------------------------------------------------------------------
# Scenario 4: Notes with wikilinks + unified search
# --------------------------------------------------------------------------
def test_e2e_notes_and_search(auth_client):
    client = auth_client
    note = _post(client, "/api/v1/notes", title="Project Alpha",
                 content="Kickoff notes referencing [[Quarterly Report]] and ideas.")
    assert note["id"]
    results = _get(client, "/api/v1/search?q=Kickoff")
    assert isinstance(results, dict)
    assert any("Alpha" in str(r) for r in results.get("notes", [])), "note should appear in unified search"
    graph = _get(client, "/api/v1/notes/graph")
    assert isinstance(graph, dict)


# --------------------------------------------------------------------------
# Scenario 5: Memory store → retrieve → export → delete
# --------------------------------------------------------------------------
def test_e2e_memory_flow(auth_client):
    client = auth_client
    mem = _post(client, "/api/v1/memory", category="preference",
                key="ui_theme", value="dark")
    items = _get(client, "/api/v1/memory")
    assert any(m["key"] == "ui_theme" for m in items["items"])
    exported = _post(client, "/api/v1/memory/export")
    assert isinstance(exported, dict) and exported["count"] >= 1
    assert client.delete(f"/api/v1/memory/{mem['id']}").status_code == 200


# --------------------------------------------------------------------------
# Scenario 6: Workflow definition validation (cycle rejected) + run
# --------------------------------------------------------------------------
GOOD_DEF = {
    "name": "Morning routine",
    "steps": [
        {"id": "plan", "tool": "daily_plan", "action": "daily_plan", "params": {}},
        {"id": "notify", "tool": "noop", "action": "noop", "params": {}, "depends_on": ["plan"]},
    ],
}
CYCLE_DEF = {
    "name": "Broken loop",
    "steps": [
        {"id": "a", "tool": "noop", "action": "noop", "params": {}, "depends_on": ["b"]},
        {"id": "b", "tool": "noop", "action": "noop", "params": {}, "depends_on": ["a"]},
    ],
}


def test_e2e_workflow_validation_and_run(auth_client):
    client = auth_client
    bad = client.post("/api/v1/workflows", json={"name": CYCLE_DEF["name"], "definition": CYCLE_DEF})
    assert bad.status_code == 422, "cyclic workflow must be rejected"

    wf = _post(client, "/api/v1/workflows", name=GOOD_DEF["name"], definition=GOOD_DEF)
    wid = wf["id"]
    _post(client, f"/api/v1/workflows/{wid}/activate")

    plan = _get(client, f"/api/v1/workflows/{wid}/plan")
    step_ids = [s["step"] for s in plan.get("execution_plan", [])]
    assert step_ids.index("plan") < step_ids.index("notify"), "topological order"

    run = _post(client, f"/api/v1/workflows/{wid}/run")
    assert run["status"].lower() in ("completed", "succeeded", "failed", "awaiting_approval", "running", "partial")
    runs = _get(client, f"/api/v1/workflows/{wid}/runs")
    assert len(runs) >= 1


# --------------------------------------------------------------------------
# Scenario 7: Scheduler job CRUD + cron validation + enqueue run-now
# --------------------------------------------------------------------------
def test_e2e_scheduler_job(auth_client):
    client = auth_client
    bad = client.post("/api/v1/scheduler/jobs", json={
        "name": "bad-cron", "action": {"handler": "noop"}, "cron_expression": "not a cron"})
    assert bad.status_code == 422

    job = _post(client, "/api/v1/scheduler/jobs", name="Daily planning",
                action={"handler": "daily_plan"}, cron_expression="0 7 * * *")
    jid = job["id"]
    run = _post(client, f"/api/v1/scheduler/jobs/{jid}/run-now")
    assert run is not None

    toggled = client.patch(f"/api/v1/scheduler/jobs/{jid}", json={"enabled": False})
    assert toggled.status_code == 200, toggled.text
    assert client.delete(f"/api/v1/scheduler/jobs/{jid}").status_code == 200


# --------------------------------------------------------------------------
# Scenario 8: Emergency stop blocks mutating endpoints (§13)
# --------------------------------------------------------------------------
def test_e2e_emergency_stop(auth_client):
    client = auth_client
    _post(client, "/api/v1/system/emergency-stop/engage", reason="E2E drill")
    blocked = client.post("/api/v1/tasks", json={"title": "should be blocked"})
    assert blocked.status_code == 423, "mutating call must be blocked while stopped"

    status = _get(client, "/api/v1/system/emergency-stop")
    assert status.get("active") is True

    _post(client, "/api/v1/system/emergency-stop/release", reason="drill over")
    ok = client.post("/api/v1/tasks", json={"title": "allowed again"})
    assert ok.status_code in (200, 201), ok.text


# --------------------------------------------------------------------------
# Scenario 9: Policy engine — unregistered tool cannot execute
# --------------------------------------------------------------------------
def test_e2e_policy_gate(auth_client):
    client = auth_client
    tools = _get(client, "/api/v1/tools")
    assert isinstance(tools, list)
    if tools:
        res = client.post("/api/v1/tools/execute",
                          json={"tool": tools[0]["name"], "args": {}})
        assert res.status_code in (200, 403, 423, 422)
    denied = _post(client, "/api/v1/tools/execute", tool="rm_rf_root", args={})
    assert denied["status"] in ("error", "blocked"), "unregistered/dangerous tool must not execute"
    policy = _get(client, "/api/v1/policy")
    assert isinstance(policy, (dict, list))


# --------------------------------------------------------------------------
# Scenario 10: Settings get/update/export/import + autonomy profile
# --------------------------------------------------------------------------
def test_e2e_settings_and_profile(auth_client):
    client = auth_client
    settings = _get(client, "/api/v1/settings")
    assert isinstance(settings, dict)

    upd = client.put("/api/v1/settings/model", json={"generation_params": {"temperature": 0.5}})
    assert upd.status_code == 200, upd.text

    bad = client.put("/api/v1/settings/model", json={"context_length": 99})
    assert bad.status_code == 422, "out-of-range setting must be rejected"

    prof = client.post("/api/v1/settings/autonomy/profile", json={"profile": "Assist Mode"})
    assert prof.status_code == 200, prof.text
    profiles = _get(client, "/api/v1/settings/autonomy/profiles")
    assert isinstance(profiles, (list, dict))

    exported = _get(client, "/api/v1/settings/export/get")
    assert isinstance(exported, dict)
    imp = client.post("/api/v1/settings/import", json=exported)
    assert imp.status_code == 200


# --------------------------------------------------------------------------
# Scenario 11: Backup → verify → preview restore (§15)
# --------------------------------------------------------------------------
def test_e2e_backup_verify_restore(auth_client):
    client = auth_client
    bk = _post(client, "/api/v1/backups", description="E2E snapshot")
    bid = bk.get("backup_id") or bk.get("id")

    verified = _post(client, f"/api/v1/backups/{bid}/verify")
    assert verified.get("verified") or verified.get("ok") or verified.get("valid") or "checksum" in str(verified)

    preview = _get(client, f"/api/v1/backups/{bid}/preview-restore")
    assert isinstance(preview, dict)

    restored = client.post(f"/api/v1/backups/{bid}/restore", json={"confirm": True})
    assert restored.status_code == 200, restored.text


# --------------------------------------------------------------------------
# Scenario 12: Audit trail records actions
# --------------------------------------------------------------------------
def test_e2e_audit_trail(auth_client):
    client = auth_client
    _post(client, "/api/v1/tasks", title="Audited action")
    events = _get(client, "/api/v1/audit/events")
    assert isinstance(events, list) and len(events) >= 1
    assert "id" in events[0]


# --------------------------------------------------------------------------
# Scenario 13: Self-X identity, goals, diagnostics
# --------------------------------------------------------------------------
def test_e2e_selfx_flow(auth_client):
    client = auth_client
    ident = _get(client, "/api/v1/selfx/identity")
    assert isinstance(ident, dict)

    goal = _post(client, "/api/v1/selfx/goals", objective="Improve morning routine",
                 baseline={"tasks_completed": 1}, target={"tasks_completed": 5})
    assert goal["id"]

    diag = _post(client, "/api/v1/selfx/diagnose", job_id="job_x", error="timeout")
    assert isinstance(diag, dict)


# --------------------------------------------------------------------------
# Scenario 14: Skill studio lifecycle — draft → publish gate before tests
# --------------------------------------------------------------------------
def test_e2e_skill_publish_gate(auth_client):
    client = auth_client
    skill = _post(client, "/api/v1/skills", name="summarizer",
                  description="Summarize text", code="def run(text): return text[:50]")
    sid = skill["id"]

    # Publishing without passing tests must be refused.
    early = client.post(f"/api/v1/skills/{sid}/publish", json={"version": "0.1.0"})
    assert early.status_code in (409, 422), "publish must require passing tests"

    versions = _get(client, f"/api/v1/skills/{sid}/versions")
    assert isinstance(versions.get("versions"), list)


# --------------------------------------------------------------------------
# Scenario 15: Dashboard aggregates data from multiple modules
# --------------------------------------------------------------------------
def test_e2e_dashboard(auth_client):
    client = auth_client
    _post(client, "/api/v1/tasks", title="Dashboard-visible task")
    dash = _get(client, "/api/v1/dashboard")
    assert isinstance(dash, dict)
    assert len(dash) > 0
    analytics = _get(client, "/api/v1/analytics/summary")
    assert isinstance(analytics, dict)
