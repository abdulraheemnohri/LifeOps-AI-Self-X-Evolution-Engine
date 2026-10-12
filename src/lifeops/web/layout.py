from fasthtml.common import *

def page_layout(title_str: str, active_page: str, body_content):
    nav_pages = [
        ("dashboard", "Dashboard", "/"),
        ("assistant", "AI Assistant", "/assistant"),
        ("tasks", "Tasks & Projects", "/tasks"),
        ("calendar", "Calendar & Routines", "/calendar"),
        ("notes", "Notes & Knowledge", "/notes"),
        ("memory", "Memory Explorer", "/memory"),
        ("research", "Research Center", "/research"),
        ("skills", "Skills Studio", "/skills"),
        ("selfx", "Self-X Control Center", "/selfx"),
        ("workflows", "Automation & Scheduler", "/workflows"),
        ("workers", "Worker Monitor", "/workers"),
        ("files", "Files & Documents", "/files"),
        ("tools", "Tools & Integrations", "/tools"),
        ("models", "Model Manager", "/models"),
        ("security", "Security & Approvals", "/security"),
        ("analytics", "Analytics & Reports", "/analytics"),
        ("backups", "Backup & Recovery", "/backups"),
        ("notifications", "Notifications", "/notifications"),
        ("settings", "Settings", "/settings"),
        ("help", "Help & About", "/help"),
    ]

    nav_items = [
        Li(
            A(label, href=path),
            cls=f"nav-item {'active' if key == active_page else ''}"
        ) for key, label, path in nav_pages
    ]

    return Html(
        Head(
            Title(f"{title_str} - LifeOps AI"),
            Link(rel="stylesheet", href="/static/css/style.css"),
            Script(src="https://unpkg.com/htmx.org@1.9.10")
        ),
        Body(
            Div(
                # Sidebar
                Div(
                    Div("LifeOps AI + Self-X", cls="sidebar-header"),
                    Ul(*nav_items, cls="nav-list"),
                    cls="sidebar"
                ),
                # Main Content
                Div(
                    # Topbar
                    Div(
                        H3(title_str, style="margin: 0; color: #f1f5f9;"),
                        Div(
                            Span("Status: Healthy", cls="badge badge-success"),
                            style="display: flex; gap: 10px; align-items: center;"
                        ),
                        cls="topbar"
                    ),
                    # Page Body
                    Div(body_content, cls="page-body"),
                    cls="main-content"
                ),
                cls="app-container"
            )
        )
    )
