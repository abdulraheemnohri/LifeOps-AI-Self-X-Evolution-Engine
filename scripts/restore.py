"""Restore a verified backup to a new destination, never overwriting existing files."""
import argparse
from pathlib import Path
from lifeops.backup import restore_backup
parser = argparse.ArgumentParser()
parser.add_argument("backup", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
restore_backup(args.backup, args.destination)
print(f"Verified backup restored to new database: {args.destination.resolve()}")
