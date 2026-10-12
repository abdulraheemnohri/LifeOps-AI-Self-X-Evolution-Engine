# Installation

## Requirements

Python 3.12 or newer; Windows 10/11 or Linux. Initial package installation requires network access. Task and note features work offline once dependencies are installed.

## Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m lifeops.app
```

## Linux

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
python -m lifeops.app
```

Open http://127.0.0.1:5001. SQLite is created at `data/lifeops.db`. Set `LIFEOPS_DATA_DIR` to choose another data directory, `LIFEOPS_DATABASE_URL` to supply a SQLAlchemy URL, or `LIFEOPS_PORT` to change the port. Run `pytest` for service tests and open `/health` for status.

## Security limitation

The initial foundation has no authentication or CSRF middleware. It binds to loopback by default. Do not expose it to an untrusted network. Setting `LIFEOPS_ALLOW_REMOTE=true` only permits a configured non-loopback bind; it does not secure the application.
