"""Create and verify a SQLite backup: python scripts/backup.py [destination]"""
from pathlib import Path
import sys
from lifeops.backup import create_backup, verify_backup
from lifeops.database import database_url
url = database_url()
if not url.startswith("sqlite:///"):
    raise SystemExit("Only SQLite file databases are supported by this script.")
source = Path(url.removeprefix("sqlite:///")).resolve()
target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else source.parent / "backups" / f"lifeops-{__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
manifest = create_backup(source, target)
print(f"Backup created: {target}")
print(f"SHA-256: {manifest['sha256']}")
print(f"Verification: {verify_backup(target)['integrity_check']}")
