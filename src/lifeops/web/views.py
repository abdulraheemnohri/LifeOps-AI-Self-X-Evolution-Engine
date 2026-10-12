from fasthtml.common import *
from lifeops.web.layout import page_layout

def render_dashboard(data=None):
    return page_layout(
        "Dashboard", "dashboard",
        Div(
            H2("Welcome to LifeOps AI"),
            P("Your autonomous productivity and self-evolution control center."),
            Div(
                Div(H4("Active Tasks"), P("3 Pending"), cls="card"),
                Div(H4("Self-X Health"), P("Operational - 100%"), cls="card"),
                Div(H4("Pending Approvals"), P("0 Awaiting"), cls="card"),
                style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;"
            )
        )
    )

def render_tasks_page(tasks):
    task_rows = [
        Tr(
            Td(str(t["id"])),
            Td(t["title"]),
            Td(Span(t["priority"].upper(), cls="badge badge-warning" if t["priority"]=="high" else "badge-success")),
            Td(t["status"]),
            Td(
                Form(
                    Input(type="hidden", name="task_id", value=str(t["id"])),
                    Input(type="hidden", name="status", value="SUCCEEDED"),
                    Button("Mark Complete", cls="btn", type="submit"),
                    action="/tasks/complete", method="post"
                ) if t["status"] != "SUCCEEDED" else Span("Done", cls="badge badge-success")
            )
        ) for t in tasks
    ]
    return page_layout(
        "Tasks & Projects", "tasks",
        Div(
            H2("Tasks & Projects Management"),
            Div(
                H3("Create New Task"),
                Form(
                    Div(Input(type="text", name="title", placeholder="Task Title", required=True, style="padding: 8px; width: 300px; margin-right: 10px;")),
                    Div(
                        Select(
                            Option("High", value="high"),
                            Option("Medium", value="medium", selected=True),
                            Option("Low", value="low"),
                            name="priority", style="padding: 8px; margin-right: 10px;"
                        ),
                        Button("Add Task", cls="btn", type="submit")
                    ),
                    action="/tasks/create", method="post", style="display: flex; gap: 10px; align-items: center; margin-bottom: 20px;"
                ),
                cls="card"
            ),
            Div(
                H3("Current Tasks"),
                Table(
                    Thead(Tr(Th("ID"), Th("Title"), Th("Priority"), Th("Status"), Th("Action"))),
                    Tbody(*task_rows),
                    style="width: 100%; text-align: left; border-collapse: collapse;"
                ) if task_rows else P("No tasks created yet."),
                cls="card"
            )
        )
    )

def render_assistant_page(conversation_history):
    msgs = [
        Div(
            Strong(f"{m['role'].capitalize()}: "),
            Span(m['content']),
            style="padding: 8px 12px; margin-bottom: 8px; background: #1a2234; border-radius: 6px;"
        ) for m in conversation_history
    ]
    return page_layout(
        "AI Assistant", "assistant",
        Div(
            H2("AI Assistant & Agent Orchestrator"),
            Div(
                Div(*msgs, id="chat-history", style="max-height: 400px; overflow-y: auto; margin-bottom: 15px;"),
                Form(
                    Input(type="text", name="prompt", placeholder="Ask LifeOps assistant or give an objective...", required=True, style="width: 70%; padding: 10px; margin-right: 10px;"),
                    Button("Send Objective", cls="btn", type="submit"),
                    action="/assistant/message", method="post"
                ),
                cls="card"
            )
        )
    )

def render_page_generic(title: str, nav_key: str, description: str):
    return page_layout(
        title, nav_key,
        Div(
            H2(title),
            P(description),
            Div(
                H4("Status & Control"),
                P("Module initialized and listening for system events."),
                cls="card"
            )
        )
    )
