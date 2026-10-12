#!/usr/bin/env bash
set -e

echo "=== Installing LifeOps AI + Self-X Evolution Engine (Linux) ==="

# Check Python version
python3 -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12+ required'"

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -e .

# Ensure data and workspace directories exist
mkdir -p data workspace logs

# Initialize database
python3 -c "from src.lifeops.storage.database import init_db; init_db()"

echo "Installation complete!"
