#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3.12 --version
if [[ ! -d .venv ]]; then python3.12 -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
mkdir -p data workspace
.venv/bin/python -c 'from lifeops.database import init_db; init_db(); print("SQLite database initialized.")'
echo "Installation complete. Run ./scripts/start_linux.sh"
