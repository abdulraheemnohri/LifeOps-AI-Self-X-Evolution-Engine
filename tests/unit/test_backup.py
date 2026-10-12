import sqlite3
from pathlib import Path
import pytest
from lifeops.backup import create_backup, verify_backup, restore_backup

def test_backup_verify_restore(tmp_path: Path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE example (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO example(value) VALUES ('persistent')")
    backup = tmp_path / "backup.db"
    manifest = create_backup(source, backup)
    assert manifest["integrity_check"] == "ok"
    assert verify_backup(backup)["verified"] is True
    restored = tmp_path / "restored.db"
    restore_backup(backup, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT value FROM example").fetchone()[0] == "persistent"
    with pytest.raises(FileExistsError):
        restore_backup(backup, restored)

def test_backup_rejects_same_path(tmp_path: Path):
    source = tmp_path / "source.db"
    sqlite3.connect(source).close()
    with pytest.raises(ValueError): create_backup(source, source)

def test_backup_detects_corruption(tmp_path: Path):
    source = tmp_path / "source.db"
    sqlite3.connect(source).close()
    backup = tmp_path / "backup.db"
    create_backup(source, backup)
    backup.write_bytes(backup.read_bytes() + b"tampered")
    with pytest.raises(ValueError): verify_backup(backup)
