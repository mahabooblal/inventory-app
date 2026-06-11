# Inventory App Backup & Disaster Recovery

## Automated Backups
- Supports PostgreSQL and SQLite
- Timestamped, compressed backups in `backups/`
- Retention policy: configurable via `BACKUP_RETENTION_DAYS` (default: 7 days)
- Automated cleanup of old backups
- Docker Compose backup service runs daily at 2am (cron)

### Environment Variables
- `DATABASE_URL`: DB connection string (Postgres or SQLite)
- `DB_TYPE`: `postgres` or `sqlite`
- `BACKUP_DIR`: Where to store backups (default: `./backups`)
- `BACKUP_RETENTION_DAYS`: Days to keep backups (default: 7)
- `BACKUP_COMPRESS`: Compress backups (default: 1/true)

## Restore Procedure
1. Place the desired backup file in `backups/`.
2. Run the restore script:
   ```sh
   DB_TYPE=postgres DATABASE_URL=... RESTORE_FILE=backups/pg_backup_YYYYMMDD_HHMMSS.sql.gz python scripts/restore.py
   # or for SQLite:
   DB_TYPE=sqlite DATABASE_URL=sqlite:///instance/app.db RESTORE_FILE=backups/sqlite_backup_YYYYMMDD_HHMMSS.db.gz python scripts/restore.py
   ```
3. The script validates the file and restores the database.

## Docker Compose Integration
- The `backup` service runs scheduled backups and stores them in a persistent volume.
- Logs are written to `backups/backup.log`.

## Health & Verification
- Backup/restore scripts log all actions and errors.
- Add `/admin/backup` dashboard for manual backup/restore and status (see app UI).
- Last-backup status endpoint planned for `/health/backup`.

## Security
- Only admins can trigger manual restore from the dashboard.

## Testing
- Unit and integration tests for backup/restore scripts are in `tests/test_backup.py`.

---
For questions, see `scripts/backup.py` and `scripts/restore.py` or contact the dev team.
