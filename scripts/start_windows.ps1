# Windows PowerShell Start Script
Write-Host "=== Starting LifeOps AI Web UI ==="
if (Test-Path "venv") {
    .\venv\Scripts\Activate.ps1
}

$env:PYTHONPATH="."
uvicorn src.lifeops.web.app_ui:app --host 127.0.0.1 --port 8000 --reload
