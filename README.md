# LifeOps AI + Self-X Evolution Engine

A local-first, browser-based productivity workspace with a staged path toward controlled AI automation.

## Current working features

- Browser UI for tasks, notes, and projects.
- Persistent SQLite records and service-level validation.
- Searchable, categorized memories and append-oriented service audit events.
- Approval records with single-decision enforcement and a deterministic action policy.
- Self-X improvement goals, evaluation records, and approval-gated proposal review.
- Health endpoint at `/health`.
- Windows and Linux setup instructions in [installation docs](docs/installation.md).

## Install

Requires Python 3.12 or newer.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
$env:LIFEOPS_HOST = "127.0.0.1"
$env:LIFEOPS_PORT = "5001"
python -m lifeops.app
```

Linux:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
LIFEOPS_HOST=127.0.0.1 LIFEOPS_PORT=5001 python -m lifeops.app
```

Open http://127.0.0.1:5001. SQLite is created at `data/lifeops.db`. Run `pytest -q` for tests and open `/health` for a basic health report.\n\nFor a fresh database, apply the versioned schema with `alembic upgrade head` (PowerShell and Linux). To inspect the current schema revision, run `alembic current`. Back up the SQLite database before applying migrations to an existing workspace.

## Honest capability and security status

**This is still a development build, not a production-ready autonomous agent.** The local productivity services work without a model. A configured model adapter and policy-enforced tool executor are not yet available; agent requests are stored as `needs_input` rather than falsely reported as executed. Self-X goals, evaluation records, and proposals are persisted, but the application does not autonomously patch or deploy its own code.

Local administrator setup, password hashing, opaque cookie sessions, and request-origin/CSRF checks have been added to the browser app; these controls still need end-to-end security review. Versioned Alembic migrations, durable background workers, real model inference, fully wired approval execution, and full browser end-to-end tests remain release blockers. Agent tool execution is policy-gated; filesystem access is confined to the configured workspace, and terminal commands are never run through a shell. Keep the server bound to loopback until the complete security suite passes. Keep the server bound to loopback and do not expose it to an untrusted network. The legacy `LIFEOPS_ALLOW_REMOTE` escape hatch is not a substitute for those protections.

Configuration defaults are non-secret. Do not commit passwords, tokens, signing keys, private databases, backups, or personal workspace files.

## Development quality checks

```bash
python -m compileall -q src tests
pytest -q
```

See [architecture](docs/architecture.md), [security notes](docs/security.md), and [troubleshooting](docs/troubleshooting.md).

## Donations

Donations are optional and must never gate core functionality. This application does not collect payment information directly.

## License

MIT.
