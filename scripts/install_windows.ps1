$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) { py -3.12 --version } else { python --version }
if (-not (Test-Path ".venv")) { if ($Python) { py -3.12 -m venv .venv } else { python -m venv .venv } }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
New-Item -ItemType Directory -Force -Path "data","workspace" | Out-Null
& .\.venv\Scripts\python.exe -c "from lifeops.database import init_db; init_db(); print('SQLite database initialized.')"
Write-Host "Installation complete. Run .\scripts\start_windows.ps1"
