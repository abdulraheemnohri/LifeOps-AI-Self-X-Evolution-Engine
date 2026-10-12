# Backup and recovery

The initial backup tool supports SQLite file databases only. It uses SQLite's online backup API for a consistent snapshot, writes a SHA-256 manifest, checks SQLite integrity, and refuses to overwrite an existing restore destination.

Create and verify a backup:

```powershell
python scripts/backup.py
```

```bash
python scripts/backup.py
```

Restore into a new file (never directly over the live database):

```bash
python scripts/restore.py data/backups/lifeops-YYYYMMDD-HHMMSS.db data/recovered/lifeops.db
```

Keep backups outside the live data directory and protect them like the original database. Hashes detect accidental/tampered changes but do not encrypt data or authenticate the manifest. Encryption and scheduled retention are not yet implemented. Test restoration before relying on a backup for disaster recovery.
