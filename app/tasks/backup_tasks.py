from datetime import datetime

from app.repositories.backup_repository import BackupRepository
from app.services.backup_service import BackupService
from app.models.audit_log import log_audit_event
import os
import subprocess
import sys
from flask import current_app


class BackupTasks:
    @staticmethod
    def scheduled_backup(user_id=None, backup_type='scheduled'):
        return BackupService.run_backup(backup_type=backup_type, created_by=user_id)

    @staticmethod
    def retention_cleanup():
        now = datetime.utcnow()
        expired = [r for r in BackupRepository.get_all() if r.retention_until and r.retention_until < now]
        for record in expired:
            BackupService.delete_backup(record.id, delete_file=True)
        return len(expired)

    @staticmethod
    def verify_all_backups():
        verified = []
        for record in BackupRepository.get_all():
            verified.append(BackupService.verify_backup(record.id))
        return verified

    @staticmethod
    def reconcile_backups(backup_dir=None):
        return BackupService.reconcile_backups(backup_dir)

    @staticmethod
    def restore_backup_task(record_id, initiated_by=None, dry_run=False):
        record = BackupRepository.get_by_id(record_id)
        if not record:
            return False, 'record_not_found'
        script = BackupService.script_path('restore.py')
        env = {
            **os.environ,
            'RESTORE_FILE': record.file_path,
            'BACKUP_DIR': BackupService.backup_dir(),
            'DATABASE_URL': current_app.config.get('SQLALCHEMY_DATABASE_URI', os.environ.get('DATABASE_URL', '')),
            'DB_TYPE': record.database_type,
        }
        if dry_run:
            # mark dry-run start in audit
            log_audit_event(initiated_by, None, 'RESTORE_DRY_RUN_STARTED', record.id, 'started')
            env['DRY_RUN'] = '1'
        try:
            result = subprocess.run([sys.executable, script], env=env, capture_output=True, text=True)
            output = (result.stdout or '') + (result.stderr or '')
            ok = result.returncode == 0
            if dry_run:
                # Do not modify DB on dry-run; only log audit result
                if ok:
                    log_audit_event(initiated_by, None, 'RESTORE_DRY_RUN_PASSED', record.id, 'passed')
                else:
                    log_audit_event(initiated_by, None, 'RESTORE_DRY_RUN_FAILED', record.id, 'failed')
                return ok, output
            else:
                BackupService.restore_backup(record.id, initiated_by, 'completed' if ok else 'failed', notes=output[-1000:])
                log_audit_event(initiated_by, None, 'RESTORE_EXECUTED', record.id, 'completed' if ok else 'failed')
                return ok, output
        except Exception as exc:
            if dry_run:
                log_audit_event(initiated_by, None, 'RESTORE_DRY_RUN_FAILED', record.id, f'error: {exc}')
                return False, str(exc)
            BackupService.restore_backup(record.id, initiated_by, 'failed', notes=str(exc))
            log_audit_event(initiated_by, None, 'RESTORE_EXECUTED', record.id, f'error: {exc}')
            return False, str(exc)
