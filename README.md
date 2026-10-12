# LifeOps AI + Self-X Evolution Engine

A local-first personal productivity platform with a browser UI and a staged path toward controlled AI automation. Current capabilities include task and note management, projects, searchable memory, audit events, approval records, and a deterministic action policy.

## Install

Python 3.12 or newer. Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m lifeops.app
```

Linux:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
python -m lifeops.app
```

Open http://127.0.0.1:5001. SQLite is created at `data/lifeops.db`. Run `pytest -q` for service tests and open `/health` for status.

## Honest feature status

The model runtime and tool executor are not configured. Agent requests are persisted with a `needs_input` status rather than pretending to execute. The policy module is deterministic, but approvals do not themselves run actions. Authentication, CSRF protection, migrations, real inference, background workers, and several advanced modules remain incomplete. Do not expose this development build to untrusted networks.

See [installation](docs/installation.md) and [architecture](docs/architecture.md). Optional donations can be linked in a later Support page; no payment details are collected by this app.

## License

MIT.
