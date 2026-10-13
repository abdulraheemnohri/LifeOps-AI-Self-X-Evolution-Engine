"""Local SQLite backup utilities using SQLite's consistent online backup API."""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote
from .manager import BackupManager

def sqlite_path(database_url: str) -> Path:
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Backup utility currently supports SQLite file databases only.")
    raw = database_url.removeprefix("sqlite:///")
    if raw == ":memory:": raise ValueError("In-memory databases cannot be backed up by this utility.")
    return Path(unquote(raw)).expanduser().resolve()

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def create_backup(source: Path, destination: Path) -> dict:
    source, destination = source.expanduser().resolve(), destination.expanduser().resolve()
    if not source.is_file(): raise FileNotFoundError(f"Database not found: {source}")
    if source == destination: raise ValueError("Backup destination must differ from the live database.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    if temporary.exists(): temporary.unlink()
    try:
        with sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True) as src:
            with sqlite3.connect(temporary) as dst:
                src.backup(dst)
                result = dst.execute("PRAGMA integrity_check").fetchone()[0]
                if result != "ok": raise RuntimeError(f"Backup integrity check failed: {result}")
        os.replace(temporary, destination)
    finally:
        if temporary.exists(): temporary.unlink()
    manifest = {
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_name": source.name,
        "backup_name": destination.name,
        "sha256": sha256_file(destination),
        "integrity_check": "ok",
    }
    destination.with_suffix(destination.suffix + ".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

def verify_backup(backup: Path) -> dict:
    backup = backup.expanduser().resolve()
    manifest_path = backup.with_suffix(backup.suffix + ".manifest.json")
    if not backup.is_file() or not manifest_path.is_file(): raise FileNotFoundError("Backup or manifest is missing.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = sha256_file(backup)
    if actual != manifest.get("sha256"): raise ValueError("Backup hash does not match manifest.")
    with sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok": raise ValueError(f"SQLite integrity check failed: {integrity}")
    manifest["verified"] = True
    return manifest

def restore_backup(backup: Path, destination: Path) -> None:
    backup, destination = backup.expanduser().resolve(), destination.expanduser().resolve()
    verify_backup(backup)
    if destination.exists(): raise FileExistsError("Restore destination already exists; refusing to overwrite.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".restore")
    try:
        with sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True) as src:
            with sqlite3.connect(temporary) as dst:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok": raise RuntimeError("Restored database failed integrity check.")
        os.replace(temporary, destination)
    finally:
        if temporary.exists(): temporary.unlink()
