#!/usr/bin/env bash
set -e

echo "=== Starting LifeOps AI Web UI ==="
if [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONPATH=.
uvicorn lifeops.main:app --host 127.0.0.1 --port 8000 --reload
