# LifeOps AI + Self-X Evolution Engine

A local-first personal productivity platform with a browser UI and a staged path toward controlled AI automation. This repository is being implemented in phases; this foundation does not claim to provide autonomous model execution or production authentication.

## Requirements

- Python 3.12 or newer
- Windows 10/11 or Linux
- Internet for initial package installation; core task/note features need no network after dependencies are installed

## Install (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m lifeops.app
```

## Install (Linux)

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
python -m lifeops.app
```

Open http://127.0.0.1:5001. The database is created automatically at `data/lifeops.db`. Set `LIFEOPS_DATA_DIR` or `LIFEOPS_DATABASE_URL` to change storage, or `LIFEOPS_PORT` to change the port. Health status is at `/health`. See [installation](docs/installation.md) and [architecture/acceptance checklist](docs/architecture.md).

## Current scope

Implemented in the foundation: SQLite task and note persistence, task completion, audit events, responsive browser UI, basic input validation, and a health endpoint. AI inference, authentication, migrations, persistent background jobs, approvals, integrations, and full Self-X repair/evaluation workflows remain planned work. Do not expose this initial build to an untrusted network.

## Security note

The application binds to loopback by default. Remote binding requires `LIFEOPS_ALLOW_REMOTE=true`, but this alone does not add authentication and must not be treated as a production deployment setting.

## License

MIT. See [LICENSE](LICENSE).
