from app import db
from app.models import BackupRecord, AuditLog
from app.services.backup_service import BackupService
from app.tasks.backup_tasks import BackupTasks


def create_backup_file(tmp_path, content=b'test'): 
    path = tmp_path / 'backup.db'
    path.write_bytes(content)
    checksum = BackupService.calculate_checksum(str(path))
    (tmp_path / 'backup.db.sha256').write_text(checksum, encoding='utf-8')
    return path


def test_restore_task_success_and_audit(admin_user, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = create_backup_file(tmp_path)
    record = BackupService.sync_filesystem()[0]

    fake_result = type('R', (), {'returncode': 0, 'stdout': 'ok', 'stderr': ''})
    monkeypatch.setattr('app.tasks.backup_tasks.subprocess.run', lambda *args, **kwargs: fake_result)

    ok, output = BackupTasks.restore_backup_task(record.id, initiated_by=admin_user)
    assert ok is True
    assert 'ok' in output
    updated = BackupRecord.query.get(record.id)
    assert updated.restore_status == 'completed'
    audit = AuditLog.query.filter_by(action='RESTORE_EXECUTED').first()
    assert audit is not None
    assert audit.user_id == admin_user.id
    assert audit.username == admin_user.username


def test_restore_task_failure(admin_user, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = create_backup_file(tmp_path)
    record = BackupService.sync_filesystem()[0]

    fake_result = type('R', (), {'returncode': 2, 'stdout': '', 'stderr': 'error'})
    monkeypatch.setattr('app.tasks.backup_tasks.subprocess.run', lambda *args, **kwargs: fake_result)

    ok, output = BackupTasks.restore_backup_task(record.id, initiated_by=admin_user)
    assert ok is False
    assert 'error' in output
    updated = BackupRecord.query.get(record.id)
    assert updated.restore_status == 'failed'
    failure_audit = AuditLog.query.filter_by(action='RESTORE_FAILED').first()
    assert failure_audit is not None


def test_restore_task_exception_updates_failed(admin_user, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = create_backup_file(tmp_path)
    record = BackupService.sync_filesystem()[0]

    def raise_error(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr('app.tasks.backup_tasks.subprocess.run', raise_error)

    ok, output = BackupTasks.restore_backup_task(record.id, initiated_by=admin_user)
    assert ok is False
    assert 'boom' in output
    updated = BackupRecord.query.get(record.id)
    assert updated.restore_status == 'failed'
    failure_audit = AuditLog.query.filter_by(action='RESTORE_FAILED').first()
    assert failure_audit is not None


def test_queue_restore_marks_queued_and_runs(admin_user, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = create_backup_file(tmp_path)
    record = BackupService.sync_filesystem()[0]

    fake_result = type('R', (), {'returncode': 0, 'stdout': 'ok', 'stderr': ''})
    monkeypatch.setattr('app.tasks.backup_tasks.subprocess.run', lambda *args, **kwargs: fake_result)

    BackupService.queue_restore(record.id, initiated_by=admin_user)
    queued = BackupRecord.query.get(record.id)
    assert queued.restore_status == 'completed'
    audit = AuditLog.query.filter_by(action='RESTORE_QUEUED').first()
    assert audit is not None
