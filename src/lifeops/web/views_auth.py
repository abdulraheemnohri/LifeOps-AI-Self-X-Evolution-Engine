"""Authentication-related view renderers."""
from fasthtml.common import *

from lifeops.web.layout import page_layout, status_badge, stat_card


def render_login_page(error: str = None, next_url: str = "/"):
    """Render login page."""
    body = Div(
        Div(
            H2("Login to LifeOps AI"),
            Form(
                Div(
                    Label("Username:", cls="form-label"),
                    Input(type="text", name="username", required=True, cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Label("Password:", cls="form-label"),
                    Input(type="password", name="password", required=True, cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Input(type="hidden", name="next", value=next_url),
                    Button("Login", type="submit", cls="btn"),
                    cls="form-actions"
                ),
                action="/auth/login", method="post", cls="login-form"
            ),
            P("Don't have an account? ", A("Create one", href="/auth/register")),
            cls="card"
        ),
    )
    return page_layout("Login", "login", body, error=error)


def render_register_page(error: str = None):
    """Render user registration page."""
    body = Div(
        Div(
            H2("Create Account"),
            Form(
                Div(
                    Label("Username:", cls="form-label"),
                    Input(type="text", name="username", placeholder="Choose a username", required=True, cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Label("Password:", cls="form-label"),
                    Input(type="password", name="password", placeholder="Minimum 12 characters", required=True, minlength="12", cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Label("Confirm Password:", cls="form-label"),
                    Input(type="password", name="confirm_password", placeholder="Confirm your password", required=True, cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Button("Create Account", type="submit", cls="btn btn-primary"),
                    cls="form-actions"
                ),
                action="/auth/register", method="post", cls="login-form"
            ),
            P(A("Already have an account? Login", href="/auth/login")),
            cls="card"
        ),
    )
    return page_layout("Register", "register", body, error=error)


def render_profile_page(user=None, sessions=None, error: str = None, flash: str = None):
    """Render user profile page."""
    if not user:
        return page_layout("Profile", "profile", Div(P("Please login first.", cls="muted")))
    
    session_rows = []
    for session in sessions or []:
        session_rows.append(Tr(
            Td(session.id),
            Td(session.created_at.strftime("%Y-%m-%d %H:%M") if session.created_at else "-"),
            Td(session.expires_at.strftime("%Y-%m-%d %H:%M") if session.expires_at else "-"),
            Td(Form(
                Input(type="hidden", name="session_id", value=session.id),
                Button("Revoke", type="submit", cls="btn btn-sm btn-danger"),
                action="/auth/session/revoke", method="post"
            ))
        ))
    
    body = Div(
        Div(
            H2(f"Profile: {user.username}"),
            Div(
                P(Strong("Username: "), user.username),
                P(Strong("Role: "), user.role),
                P(Strong("Created: "), user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "-"),
                cls="profile-info"
            ),
            cls="card"
        ),
        Div(
            H3("Change Password"),
            Form(
                Div(
                    Label("Old Password:", cls="form-label"),
                    Input(type="password", name="old_password", required=True, cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Label("New Password:", cls="form-label"),
                    Input(type="password", name="new_password", placeholder="Minimum 12 characters", required=True, minlength="12", cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Label("Confirm New Password:", cls="form-label"),
                    Input(type="password", name="confirm_password", required=True, cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Button("Change Password", type="submit", cls="btn btn-secondary"),
                    cls="form-actions"
                ),
                action="/auth/change-password", method="post", cls="login-form"
            ),
            cls="card"
        ),
        Div(
            H3("Active Sessions"),
            _table(["Session ID", "Created", "Expires", "Action"], session_rows, empty_msg="No active sessions."),
            cls="card"
        ),
        Div(
            Form(
                Button("Revoke All Other Sessions", type="submit", cls="btn btn-danger"),
                action="/auth/session/revoke-all", method="post"
            ),
            cls="card"
        ),
        Div(
            A("Logout", href="/auth/logout", cls="btn btn-secondary"),
            cls="card"
        ),
    )
    return page_layout("Profile", "profile", body, error=error, flash=flash)


def render_users_page(users=None, error: str = None, flash: str = None):
    """Render user management page (admin only)."""
    rows = []
    for user in users or []:
        rows.append(Tr(
            Td(user.id),
            Td(user.username),
            Td(user.role),
            Td(user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "-"),
            Td(Form(
                Input(type="hidden", name="user_id", value=user.id),
                Button("Edit", type="submit", cls="btn btn-sm"),
                action="/auth/users/edit", method="post"
            )),
            Td(Form(
                Input(type="hidden", name="user_id", value=user.id),
                Button("Delete", type="submit", cls="btn btn-sm btn-danger"),
                action="/auth/users/delete", method="post"
            ))
        ))
    
    body = Div(
        Div(
            H2("Users"),
            Div(
                H3("Create User"),
                Form(
                    Div(
                        Label("Username:", cls="form-label"),
                        Input(type="text", name="username", required=True, cls="form-input"),
                        cls="form-group"
                    ),
                    Div(
                        Label("Password:", cls="form-label"),
                        Input(type="password", name="password", placeholder="Minimum 12 characters", required=True, minlength="12", cls="form-input"),
                        cls="form-group"
                    ),
                    Div(
                        Label("Role:", cls="form-label"),
                        Select(
                            Option("user", value="user"),
                            Option("admin", value="admin"),
                            name="role", cls="form-input"
                        ),
                        cls="form-group"
                    ),
                    Div(
                        Button("Create User", type="submit", cls="btn btn-primary"),
                        cls="form-actions"
                    ),
                    action="/auth/users/create", method="post", cls="login-form"
                ),
                cls="card-section"
            ),
            Div(
                H3("All Users"),
                _table(["ID", "Username", "Role", "Created", "", ""], rows, empty_msg="No users yet."),
                cls="card-section"
            ),
            cls="card"
        ),
    )
    return page_layout("User Management", "users", body, error=error, flash=flash)


def render_user_edit_page(user=None, error: str = None, flash: str = None):
    """Render user edit page."""
    if not user:
        return page_layout("Edit User", "users", Div(P("User not found.", cls="error")))
    
    body = Div(
        Div(
            H2(f"Edit User: {user.username}"),
            Form(
                Input(type="hidden", name="user_id", value=user.id),
                Div(
                    Label("Username:", cls="form-label"),
                    Input(type="text", name="username", value=user.username, required=True, cls="form-input"),
                    cls="form-group"
                ),
                Div(
                    Label("Role:", cls="form-label"),
                    Select(
                        Option("user", value="user", selected=user.role == "user"),
                        Option("admin", value="admin", selected=user.role == "admin"),
                        name="role", cls="form-input"
                    ),
                    cls="form-group"
                ),
                Div(
                    Button("Save", type="submit", cls="btn btn-primary"),
                    " ",
                    A("Cancel", href="/auth/users", cls="btn btn-secondary"),
                    cls="form-actions"
                ),
                action="/auth/users/update", method="post", cls="login-form"
            ),
            cls="card"
        ),
    )
    return page_layout("Edit User", "users", body, error=error, flash=flash)


# Helper function for tables
def _table(headers, rows, empty_msg="Nothing here yet."):
    if not rows:
        return P(empty_msg, cls="muted")
    return Table(
        Thead(Tr(*[Th(h) for h in headers])),
        Tbody(*rows), cls="data-table")
