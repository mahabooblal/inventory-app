import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

from flask import current_app
from werkzeug.utils import secure_filename

from app.repositories.backup_repository import BackupRepository
from app.models.audit_log import log_audit_event


BACKUP_EXTENSIONS = ('.sql', '.sql.gz', '.db', '.db.gz')


class BackupService:
    @staticmethod
    def backup_dir():
        backup_dir = current_app.config.get('BACKUP_DIR') or os.environ.get('BACKUP_DIR') or './backups'
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @staticmethod
    def retention_days():
        return int(current_app.config.get('BACKUP_RETENTION_DAYS') or os.environ.get('BACKUP_RETENTION_DAYS', '7'))

    @staticmethod
    def script_path(script_name):
        return os.path.abspath(os.path.join(current_app.root_path, '..', 'scripts', script_name))

    @staticmethod
    def calculate_checksum(file_path):
        import hashlib

        digest = hashlib.sha256()
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(8192), b''):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def checksum_from_sidecar(file_path):
        sidecar_path = file_path + '.sha256'
        if not os.path.exists(sidecar_path):
            return None
        with open(sidecar_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    @staticmethod
    def infer_database_type(file_name):
        return 'postgres' if '.sql' in file_name else 'sqlite'

    @staticmethod
    def is_backup_file(file_name):
        return file_name.endswith(BACKUP_EXTENSIONS)

    @staticmethod
    def safe_backup_path(file_name):
        safe_name = secure_filename(file_name)
        if safe_name != file_name or not BackupService.is_backup_file(file_name):
            raise ValueError('Invalid backup filename.')
        backup_dir = os.path.abspath(BackupService.backup_dir())
        file_path = os.path.abspath(os.path.join(backup_dir, safe_name))
        if os.path.commonpath([backup_dir, file_path]) != backup_dir:
            raise ValueError('Invalid backup path.')
        return file_path

    @staticmethod
    def create_backup(
        backup_type,
        database_type=None,
        file_name=None,
        file_path=None,
        file_size=None,
        checksum=None,
        status='ok',
        created_by=None,
        retention_days=None,
        notes=None,
    ):
        retention_days = BackupService.retention_days() if retention_days is None else retention_days
        now = datetime.utcnow()
        record = BackupRepository.create(
            backup_type=backup_type,
            database_type=database_type or BackupService.infer_database_type(file_name or ''),
            file_name=file_name,
            file_path=file_path,
            file_size=file_size or 0,
            checksum=checksum or '',
            status=status,
            created_at=now,
            retention_until=now + timedelta(days=retention_days),
            created_by=getattr(created_by, 'id', created_by),
            notes=notes,
        )
        log_audit_event(created_by, None, 'BACKUP_CREATED' if status == 'ok' else 'BACKUP_FAILED', record.id, status)
        return record

    @staticmethod
    def upsert_file_record(file_path, backup_type='manual', created_by=None, status=None, notes=None):
        file_name = os.path.basename(file_path)
        checksum = BackupService.checksum_from_sidecar(file_path) or BackupService.calculate_checksum(file_path)
        sidecar_ok = BackupService.checksum_from_sidecar(file_path) == checksum if os.path.exists(file_path + '.sha256') else False
        status = status or ('ok' if sidecar_ok else 'missing_checksum')
        existing = BackupRepository.get_by_filename(file_name)
        values = {
            'backup_type': backup_type,
            'database_type': BackupService.infer_database_type(file_name),
            'file_name': file_name,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'checksum': checksum,
            'status': status,
            'created_at': datetime.utcnow(),
            'retention_until': datetime.utcnow() + timedelta(days=BackupService.retention_days()),
            'created_by': getattr(created_by, 'id', created_by),
            'notes': notes,
        }
        if existing:
            values.pop('file_name')
            values.pop('created_at')
            values.pop('created_by')
            return BackupRepository.update(existing.id, **values)
        record = BackupRepository.create(**values)
        log_audit_event(created_by, None, 'BACKUP_CREATED' if status == 'ok' else 'BACKUP_FAILED', record.id, status)
        return record

    @staticmethod
    def run_backup(backup_type='manual', created_by=None):
        script = BackupService.script_path('backup.py')
        env = {
            **os.environ,
            'BACKUP_DIR': BackupService.backup_dir(),
            'DATABASE_URL': current_app.config.get('SQLALCHEMY_DATABASE_URI', os.environ.get('DATABASE_URL', '')),
            'BACKUP_RETENTION_DAYS': str(BackupService.retention_days()),
        }
        env.setdefault('DB_TYPE', 'sqlite' if env['DATABASE_URL'].startswith('sqlite:///') else 'postgres')
        result = subprocess.run([sys.executable, script], env=env, capture_output=True, text=True)
        output = (result.stdout or '') + (result.stderr or '')
        if result.returncode != 0:
            BackupService.create_backup(
                backup_type=backup_type,
                database_type=env['DB_TYPE'],
                file_name=f'failed_backup_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
                file_path='',
                file_size=0,
                checksum='',
                status='failed',
                created_by=created_by,
                notes=output[-1000:],
            )
            return False, output

        match = re.search(r'Backup complete:\s+(.+?)\s+\(sha256:', output)
        if not match:
            return False, output or 'Backup finished but output did not include a backup path.'
        record = BackupService.upsert_file_record(match.group(1).strip(), backup_type=backup_type, created_by=created_by)
        return True, record

    @staticmethod
    def verify_backup(record_id, notes=None):
        record = BackupRepository.get_by_id(record_id)
        if not record:
            return None
        if not record.file_path or not os.path.exists(record.file_path):
            return BackupRepository.update(
                record_id,
                status='missing',
                verified_at=datetime.utcnow(),
                verification_status='missing',
                notes=notes,
            )
        actual = BackupService.calculate_checksum(record.file_path)
        expected = BackupService.checksum_from_sidecar(record.file_path) or record.checksum
        verification_status = 'verified' if actual == expected else 'corrupt'
        status = 'ok' if verification_status == 'verified' else 'corrupt'
        updated = BackupRepository.update(
            record_id,
            checksum=actual,
            status=status,
            verified_at=datetime.utcnow(),
            verification_status=verification_status,
            notes=notes,
        )
        log_audit_event(record.creator, None, 'BACKUP_VERIFIED', record.id, verification_status)
        return updated

    @staticmethod
    def restore_backup(record_id, restored_by, restore_status='completed', notes=None):
        record = BackupRepository.update(
            record_id,
            restored_by=getattr(restored_by, 'id', restored_by),
            restore_timestamp=datetime.utcnow(),
            restore_status=restore_status,
            notes=notes,
        )
        if record:
            log_audit_event(restored_by, None, 'RESTORE_COMPLETED' if restore_status == 'completed' else 'RESTORE_FAILED', record.id, restore_status)
        return record

    @staticmethod
    def queue_restore(record_id, initiated_by=None):
        # mark restore as queued and enqueue a background task
        record = BackupRepository.update(record_id, restore_status='queued')
        log_audit_event(initiated_by, None, 'RESTORE_QUEUED', record_id, 'queued')
        # Use task runner (can be swapped with Celery/RQ later)
        # In testing mode the task runner will execute synchronously
        from app.tasks.backup_tasks import BackupTasks
        from app.tasks.runner import task_runner
        return task_runner.enqueue(BackupTasks.restore_backup_task, record_id, initiated_by, dry_run=False)

    @staticmethod
    def queue_restore_dry_run(record_id, initiated_by=None):
        # enqueue a dry-run restore validation (no data modification)
        # mark restore as queued for dry-run and enqueue task with dry_run=True
        record = BackupRepository.update(record_id, restore_status='queued')
        log_audit_event(initiated_by, None, 'RESTORE_QUEUED', record_id, 'queued')
        from app.tasks.backup_tasks import BackupTasks
        from app.tasks.runner import task_runner
        return task_runner.enqueue(BackupTasks.restore_backup_task, record_id, initiated_by, dry_run=True)

    @staticmethod
    def delete_backup(record_id, delete_file=False):
        record = BackupRepository.get_by_id(record_id)
        if not record:
            return False
        creator = getattr(record, 'creator', None)
        if delete_file and record.file_path and os.path.exists(record.file_path):
            os.remove(record.file_path)
            sidecar_path = record.file_path + '.sha256'
            if os.path.exists(sidecar_path):
                os.remove(sidecar_path)
        BackupRepository.delete(record_id)
        log_audit_event(creator, None, 'BACKUP_DELETED', record.id, 'deleted')
        return True

    @staticmethod
    def sync_filesystem(backup_dir=None):
        backup_dir = backup_dir or BackupService.backup_dir()
        if not os.path.isdir(backup_dir):
            return []
        records = []
        for file_name in sorted(os.listdir(backup_dir)):
            file_path = os.path.join(backup_dir, file_name)
            if os.path.isfile(file_path) and BackupService.is_backup_file(file_name):
                records.append(BackupService.upsert_file_record(file_path, backup_type='external'))
        return records

    @staticmethod
    def reconcile_backups(backup_dir=None):
        backup_dir = backup_dir or BackupService.backup_dir()
        missing_files = BackupRepository.find_missing_files()
        orphan_files = BackupRepository.find_orphan_files(backup_dir)
        checksum_mismatches = []
        for record in BackupRepository.get_all():
            if record.file_path and os.path.exists(record.file_path):
                actual = BackupService.calculate_checksum(record.file_path)
                expected = BackupService.checksum_from_sidecar(record.file_path) or record.checksum
                if expected and actual != expected:
                    checksum_mismatches.append(record)
        return {
            'missing_files': missing_files,
            'orphan_files': orphan_files,
            'checksum_mismatches': checksum_mismatches,
        }

    @staticmethod
    def get_backup_by_filename(file_name):
        return BackupRepository.get_by_filename(file_name)

    @staticmethod
    def get_latest_backup():
        return BackupRepository.get_latest()

    @staticmethod
    def get_all_backups():
        return BackupRepository.get_all()

    @staticmethod
    def get_paginated_backups(page=1, per_page=20):
        return BackupRepository.get_paginated(page=page, per_page=per_page)
