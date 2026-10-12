from fasthtml.common import *

NAV_PAGES = [
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


def status_badge(value):
    return Span(str(value), cls=f"badge badge-{str(value).lower()}")


def stat_card(label, value, elem_id=None):
    return Div(Span(str(value), cls="value", id=elem_id),
               Span(label, cls="label"), cls="stat-card")


def page_layout(title_str: str, active_page: str, body_content, flash: str = None,
                error: str = None):
    nav_items = [
        Li(A(label, href=path),
           cls=f"nav-item {'active' if key == active_page else ''}")
        for key, label, path in NAV_PAGES
    ]

    flash_bar = None
    if flash:
        flash_bar = Div(flash, cls="flash")
    elif error:
        flash_bar = Div(error, cls="flash error")

    return Html(
        Head(
            Title(f"{title_str} - LifeOps AI"),
            Link(rel="stylesheet", href="/static/css/style.css"),
            Script(src="/static/js/app.js", defer=True),
        ),
        Body(
            Div(
                Div(
                    Div("LifeOps AI + Self-X", cls="sidebar-header"),
                    Ul(*nav_items, cls="nav-list"),
                    cls="sidebar",
                ),
                Div(
                    Div(
                        H3(title_str, style="margin:0;color:#f1f5f9;"),
                        Div(
                            Span(cls="live-dot", id="live-dot"),
                            Span("Offline", cls="live-status", id="live-label"),
                            style="display:flex;gap:8px;align-items:center;",
                        ),
                        cls="topbar",
                    ),
                    Div(
                        *( [flash_bar] if flash_bar is not None else [] )
                        + [Div(body_content, cls="page-body")],
                        cls="main-area",
                    ),
                ),
                cls="app-shell",
            )
        ),
    )
