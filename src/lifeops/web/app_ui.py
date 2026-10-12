import os
from fasthtml.common import FastHTML, serve, RedirectResponse
from starlette.staticfiles import StaticFiles
from src.lifeops.storage.database import get_session_factory, get_engine, init_db
from src.lifeops.lifeops.tasks import TaskService
from src.lifeops.storage.models import TaskStatus
from src.lifeops.web.views import render_dashboard, render_tasks_page, render_assistant_page, render_page_generic

app = FastHTML()

# Mount static files
os.makedirs("src/lifeops/web/static/css", exist_ok=True)
app.mount("/static", StaticFiles(directory="src/lifeops/web/static"), name="static")

# Mock session chat history
chat_history = [
    {"role": "assistant", "content": "Hello! I am your LifeOps AI assistant. How can I assist you today?"}
]

def get_db_session():
    engine = get_engine()
    init_db(engine)
    sf = get_session_factory(engine)
    return sf()

@app.get("/")
def home():
    return render_dashboard()

@app.get("/assistant")
def page_assistant():
    return render_assistant_page(chat_history)

@app.post("/assistant/message")
def post_assistant_message(prompt: str):
    chat_history.append({"role": "user", "content": prompt})
    chat_history.append({"role": "assistant", "content": f"Understood objective: '{prompt}'. Deconstructing into execution steps..."})
    return RedirectResponse(url="/assistant", status_code=303)

@app.get("/tasks")
def page_tasks():
    db = get_db_session()
    svc = TaskService(db)
    tasks = svc.list_tasks()
    task_list = [{"id": t.id, "title": t.title, "priority": t.priority, "status": t.status.value} for t in tasks]
    db.close()
    return render_tasks_page(task_list)

@app.post("/tasks/create")
def post_create_task(title: str, priority: str = "medium"):
    db = get_db_session()
    svc = TaskService(db)
    svc.create_task(title=title, priority=priority)
    db.close()
    return RedirectResponse(url="/tasks", status_code=303)

@app.post("/tasks/complete")
def post_complete_task(task_id: int):
    db = get_db_session()
    svc = TaskService(db)
    svc.update_task_status(task_id, TaskStatus.SUCCEEDED)
    db.close()
    return RedirectResponse(url="/tasks", status_code=303)

@app.get("/calendar")
def page_calendar():
    return render_page_generic("Calendar & Routines", "calendar", "Events, recurring routines, and daily planning summaries.")

@app.get("/notes")
def page_notes():
    return render_page_generic("Notes & Knowledge", "notes", "Markdown notes, backlinks, and document indexing.")

@app.get("/memory")
def page_memory():
    return render_page_generic("Memory Explorer", "memory", "Search, inspect, edit, and export agent memories.")

@app.get("/research")
def page_research():
    return render_page_generic("Research Center", "research", "Autonomous research jobs, web sources, and citation reports.")

@app.get("/skills")
def page_skills():
    return render_page_generic("Skills Studio", "skills", "Author, test, validate, publish, and manage Self-X skills.")

@app.get("/selfx")
def page_selfx():
    return render_page_generic("Self-X Control Center", "selfx", "Self-identity, health diagnostics, goals, evaluations, and improvement proposals.")

@app.get("/workflows")
def page_workflows():
    return render_page_generic("Automation & Scheduler", "workflows", "Visual trigger workflows, background jobs, and recurrence rules.")

@app.get("/workers")
def page_workers():
    return render_page_generic("Worker Monitor", "workers", "Active background workers, task queues, and resource utilization.")

@app.get("/files")
def page_files():
    return render_page_generic("Files & Documents", "files", "Indexed local directories, document extractions, and search.")

@app.get("/tools")
def page_tools():
    return render_page_generic("Tools & Integrations", "tools", "Registered tools, permissions, and external integrations.")

@app.get("/models")
def page_models():
    return render_page_generic("Model Manager", "models", "Local LiteRT-LM runtime detection, model selection, and parameters.")

@app.get("/security")
def page_security():
    return render_page_generic("Security & Approvals", "security", "Pending action approvals, policy rules, and audit trail.")

@app.get("/analytics")
def page_analytics():
    return render_page_generic("Analytics & Reports", "analytics", "Productivity metrics, agent success rates, and evaluation history.")

@app.get("/backups")
def page_backups():
    return render_page_generic("Backup & Recovery", "backups", "Database snapshots, backup verification, and disaster recovery.")

@app.get("/notifications")
def page_notifications():
    return render_page_generic("Notifications", "notifications", "System alerts, task reminders, and action notifications.")

@app.get("/settings")
def page_settings():
    return render_page_generic("Settings", "settings", "Comprehensive application configuration and autonomy profiles.")

@app.get("/help")
def page_help():
    return render_page_generic("Help & About", "help", "Documentation, troubleshooting guides, version info, and voluntary support.")
