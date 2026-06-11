import types

from app.services.backup_service import BackupService
from app.tasks.backup_tasks import BackupTasks
from app.models import AuditLog, BackupRecord


def create_backup_file(tmp_path, content=b'test'):
    path = tmp_path / 'backup.db'
    path.write_bytes(content)
    checksum = BackupService.calculate_checksum(str(path))
    (tmp_path / 'backup.db.sha256').write_text(checksum, encoding='utf-8')
    return path


def test_dry_run_success_and_audit(admin_user, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = create_backup_file(tmp_path)
    record = BackupService.sync_filesystem()[0]

    fake_result = types.SimpleNamespace(returncode=0, stdout='{"result":"PASS"}', stderr='')
    monkeypatch.setattr('app.tasks.backup_tasks.subprocess.run', lambda *a, **k: fake_result)

    ok, output = BackupTasks.restore_backup_task(record.id, initiated_by=admin_user, dry_run=True)
    assert ok is True
    assert 'PASS' in output
    started = AuditLog.query.filter_by(action='RESTORE_DRY_RUN_STARTED').first()
    assert started is not None
    passed = AuditLog.query.filter_by(action='RESTORE_DRY_RUN_PASSED').first()
    assert passed is not None
    assert passed.user_id == admin_user.id


def test_dry_run_invalid_checksum(admin_user, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = create_backup_file(tmp_path)
    record = BackupService.sync_filesystem()[0]

    fake_result = types.SimpleNamespace(returncode=2, stdout='', stderr='Checksum mismatch')
    monkeypatch.setattr('app.tasks.backup_tasks.subprocess.run', lambda *a, **k: fake_result)

    ok, output = BackupTasks.restore_backup_task(record.id, initiated_by=admin_user, dry_run=True)
    assert ok is False
    assert 'Checksum' in output or 'Checksum' in (fake_result.stderr)
    failed = AuditLog.query.filter_by(action='RESTORE_DRY_RUN_FAILED').first()
    assert failed is not None


def test_dry_run_missing_backup_file(admin_user, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    # create a DB record pointing to a missing file
    record = BackupService.create_backup(
        backup_type='manual',
        database_type='sqlite',
        file_name='missing.db',
        file_path=str(tmp_path / 'missing.db'),
        file_size=0,
        checksum='',
        status='ok',
        created_by=admin_user.id,
    )

    fake_result = types.SimpleNamespace(returncode=1, stdout='', stderr='RESTORE_FILE not set or does not exist')
    monkeypatch.setattr('app.tasks.backup_tasks.subprocess.run', lambda *a, **k: fake_result)

    ok, output = BackupTasks.restore_backup_task(record.id, initiated_by=admin_user, dry_run=True)
    assert ok is False
    failed = AuditLog.query.filter_by(action='RESTORE_DRY_RUN_FAILED').first()
    assert failed is not None


def test_restore_route_dry_run_permission_denied(app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    with app.test_client() as client:
        resp = client.post('/admin/backup/restore/some.db', data={'dry_run': '1'}, follow_redirects=False)
        assert resp.status_code in (302, 403)
