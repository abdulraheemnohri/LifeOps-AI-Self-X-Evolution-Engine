"""Backup & restore manager implementing spec section 15.

Backups are consistent SQLite snapshots (sqlite3 backup API) plus a JSON
manifest with versions, timestamps, and SHA-256 hashes. Verification re-hashes
archive contents; restore previews destination state and verifies integrity
after copying.
"""
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import zipfile
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from lifeops.storage.models import BackupRecord, Base


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class BackupManager:
    def __init__(self, db: DBSession, db_path: str = "data/lifeops.db",
                 backup_dir: str = "data/backups"):
        self.db = db
        self.db_path = db_path
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self, description: str = "", include_files: Optional[List[str]] = None) -> Dict[str, Any]:
        backup_id = f"bkp_{uuid.uuid4().hex[:12]}"
        archive_path = os.path.join(self.backup_dir, f"{backup_id}.zip")
        staging = os.path.join(self.backup_dir, f"stage_{backup_id}")
        os.makedirs(staging, exist_ok=True)
        try:
            snap = os.path.join(staging, "lifeops.db")
            if os.path.exists(self.db_path):
                src = sqlite3.connect(self.db_path)
                dst = sqlite3.connect(snap)
                with dst:
                    src.backup(dst)
                src.close()
                dst.close()
            else:
                con = sqlite3.connect(snap)
                Base.metadata.create_all(bind=con)
                con.close()
            extra_hashes = {}
            for fp in (include_files or []):
                if os.path.isfile(fp):
                    dest = os.path.join(staging, "files", os.path.basename(fp))
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(fp, dest)
                    extra_hashes[os.path.basename(fp)] = sha256_file(dest)
            manifest = {
                "backup_id": backup_id,
                "app_version": "0.1.0",
                "created_at": datetime.datetime.utcnow().isoformat(),
                "description": description,
                "database_sha256": sha256_file(snap),
                "file_hashes": extra_hashes,
            }
            with open(os.path.join(staging, "manifest.json"), "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=2)
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _d, files in os.walk(staging):
                    for f in files:
                        full = os.path.join(root, f)
                        zf.write(full, os.path.relpath(full, staging))
            rec = BackupRecord(id=backup_id, filepath=archive_path,
                                file_hash=sha256_file(archive_path), verified=False)
            self.db.add(rec)
            self.db.commit()
            self.db.refresh(rec)
            return {"backup_id": backup_id, "filepath": archive_path, "manifest": manifest}
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        rec = self.db.get(BackupRecord, backup_id)
        if not rec:
            raise LookupError("backup not found")
        if not os.path.exists(rec.filepath):
            rec.verified = False
            self.db.commit()
            return {"verified": False, "reason": "archive missing"}
        if sha256_file(rec.filepath) != rec.file_hash:
            rec.verified = False
            self.db.commit()
            return {"verified": False, "reason": "archive hash mismatch"}
        tmp = os.path.join(self.backup_dir, f"verify_{backup_id}")
        try:
            with zipfile.ZipFile(rec.filepath) as zf:
                # Guard against zip path traversal
                for name in zf.namelist():
                    real = os.path.realpath(os.path.join(tmp, name))
                    if not real.startswith(os.path.realpath(tmp)):
                        return {"verified": False, "reason": "unsafe path in archive"}
                zf.extractall(tmp)
            with open(os.path.join(tmp, "manifest.json"), encoding="utf-8") as fh:
                manifest = json.load(fh)
            ok = sha256_file(os.path.join(tmp, "lifeops.db")) == manifest["database_sha256"]
            reason = None if ok else "database snapshot hash mismatch"
            if ok:
                con = sqlite3.connect(os.path.join(tmp, "lifeops.db"))
                try:
                    con.execute("PRAGMA integrity_check").fetchone()
                    tables = [r[0] for r in con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")]
                    if "tasks" not in tables:
                        ok, reason = False, "snapshot missing expected tables"
                finally:
                    con.close()
            rec.verified = ok
            self.db.commit()
            return {"verified": ok, "reason": reason, "manifest": manifest}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def list_backups(self) -> List[Dict[str, Any]]:
        rows = self.db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).all()
        return [{"id": r.id, "filepath": r.filepath, "verified": r.verified,
                  "created_at": r.created_at.isoformat()} for r in rows]

    def preview_restore(self, backup_id: str) -> Dict[str, Any]:
        rec = self.db.get(BackupRecord, backup_id)
        if not rec:
            raise LookupError("backup not found")
        verification = self.verify_backup(backup_id)
        return {"backup_id": backup_id, "destination": self.db_path,
                 "destination_exists": os.path.exists(self.db_path),
                 "verification": verification,
                 "can_restore": verification.get("verified", False)}

    def restore(self, backup_id: str, destination: Optional[str] = None,
                 require_verified: bool = True) -> Dict[str, Any]:
        dest = destination or self.db_path
        rec = self.db.get(BackupRecord, backup_id)
        if not rec:
            raise LookupError("backup not found")
        if require_verified and not rec.verified:
            v = self.verify_backup(backup_id)
            if not v.get("verified"):
                raise ValueError(f"backup failed verification: {v.get('reason')}")
        tmp = os.path.join(self.backup_dir, f"restore_{backup_id}")
        try:
            with zipfile.ZipFile(rec.filepath) as zf:
                zf.extractall(tmp)
            snap = os.path.join(tmp, "lifeops.db")
            if os.path.exists(dest):
                shutil.copy2(dest, dest + ".pre-restore.bak")
            shutil.copy2(snap, dest)
            con = sqlite3.connect(dest)
            try:
                integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
                task_count = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            finally:
                con.close()
            return {"restored": True, "destination": dest,
                     "integrity_check": integrity, "task_count_after_restore": task_count}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def apply_retention(self, keep: int = 10) -> List[str]:
        removed = []
        rows = self.db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).all()
        for old in rows[keep:]:
            if os.path.exists(old.filepath):
                os.remove(old.filepath)
            removed.append(old.id)
            self.db.delete(old)
        self.db.commit()
        return removed
