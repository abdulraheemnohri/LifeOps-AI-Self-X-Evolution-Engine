# Windows PowerShell Install Script
Write-Host "=== Installing LifeOps AI + Self-X Evolution Engine (Windows) ==="

if (-not (Test-Path "venv")) {
    python -m venv venv
}

.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e .

New-Item -ItemType Directory -Force -Path "data", "workspace", "logs"

python -c "from src.lifeops.storage.database import init_db; init_db()"

Write-Host "Installation complete!"
