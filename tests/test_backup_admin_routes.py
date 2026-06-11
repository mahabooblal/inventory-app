import types

from app import db
from app.models import BackupRecord, AuditLog
from app.services.backup_service import BackupService


def test_restore_route_queues_and_runs_task(admin_client, app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    # create backup file
    backup_file = tmp_path / 'sqlite_backup_20260531_130000.db'
    backup_file.write_bytes(b'data')
    checksum = BackupService.calculate_checksum(str(backup_file))
    (tmp_path / f'{backup_file.name}.sha256').write_text(checksum, encoding='utf-8')

    # sync to create DB record
    record = BackupService.sync_filesystem()[0]

    # mock subprocess.run to simulate successful restore
    fake_result = types.SimpleNamespace(returncode=0, stdout='Restore ok', stderr='')
    monkeypatch.setattr('subprocess.run', lambda *a, **k: fake_result)

    response = admin_client.post(f'/admin/backup/restore/{record.file_name}')
    assert response.status_code in (302, 303)

    # Task runner in testing mode runs synchronously; record should be updated
    updated = BackupRecord.query.get(record.id)
    assert updated.restore_status == 'completed'

    # Audit logs should contain queued and executed events
    actions = {a.action for a in AuditLog.query.all()}
    assert 'RESTORE_QUEUED' in actions
    assert 'RESTORE_EXECUTED' in actions or 'RESTORE_COMPLETED' in actions


def test_verify_route_flashes_success(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = tmp_path / 'sqlite_backup_20260531_130000.db'
    backup_file.write_bytes(b'data')
    checksum = BackupService.calculate_checksum(str(backup_file))
    (tmp_path / f'{backup_file.name}.sha256').write_text(checksum, encoding='utf-8')

    record = BackupService.sync_filesystem()[0]
    response = admin_client.post(f'/admin/backup/verify/{record.file_name}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Checksum valid.' in response.data


def test_delete_route_removes_backup(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = tmp_path / 'sqlite_backup_20260531_130000.db'
    backup_file.write_bytes(b'data')
    checksum = BackupService.calculate_checksum(str(backup_file))
    (tmp_path / f'{backup_file.name}.sha256').write_text(checksum, encoding='utf-8')

    record = BackupService.sync_filesystem()[0]
    response = admin_client.post(f'/admin/backup/delete/{record.file_name}', follow_redirects=True)
    assert response.status_code == 200
    assert BackupRecord.query.get(record.id) is None
    assert not backup_file.exists()


def test_manual_backup_route_success(admin_client, monkeypatch, app):
    monkeypatch.setattr('app.routes.backup_admin.BackupService.run_backup', lambda backup_type, created_by: (True, 'ok'))
    response = admin_client.post('/admin/backup/run', follow_redirects=True)
    assert response.status_code == 200
    assert b'Backup completed.' in response.data


def test_manual_backup_route_failure_shows_error(admin_client, monkeypatch, app):
    monkeypatch.setattr('app.routes.backup_admin.BackupService.run_backup', lambda backup_type, created_by: (False, 'disk full'))
    response = admin_client.post('/admin/backup/run', follow_redirects=True)
    assert response.status_code == 200
    assert b'Backup failed: disk full' in response.data


def test_download_backup_route_unknown_file_returns_404(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    response = admin_client.get('/admin/backup/download/unknown.db')
    assert response.status_code == 404


def test_verify_route_missing_backup_returns_404(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    response = admin_client.post('/admin/backup/verify/unknown.db')
    assert response.status_code == 404


def test_restore_route_missing_backup_returns_404(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    response = admin_client.post('/admin/backup/restore/unknown.db')
    assert response.status_code == 404


def test_delete_route_missing_backup_returns_404(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    response = admin_client.post('/admin/backup/delete/unknown.db')
    assert response.status_code == 404


def test_delete_route_failure_logs_and_flashes(admin_client, monkeypatch, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = tmp_path / 'sqlite_backup_20260531_130000.db'
    backup_file.write_bytes(b'data')
    checksum = BackupService.calculate_checksum(str(backup_file))
    (tmp_path / f'{backup_file.name}.sha256').write_text(checksum, encoding='utf-8')
    record = BackupService.sync_filesystem()[0]

    def fake_delete(record_id, delete_file=True):
        raise RuntimeError('delete failed')

    monkeypatch.setattr('app.routes.backup_admin.BackupService.delete_backup', fake_delete)
    response = admin_client.post(f'/admin/backup/delete/{record.file_name}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Delete failed.' in response.data
    audit = AuditLog.query.filter_by(action='backup_delete').first()
    assert audit is not None
    assert 'error: delete failed' in audit.result or 'delete failed' in audit.result


def test_dashboard_route_shows_backup_summary(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    response = admin_client.get('/admin/backup/')
    assert response.status_code == 200
    assert b'Backup' in response.data


def test_download_backup_route_sends_file(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = tmp_path / 'sqlite_backup_20260531_130000.db'
    backup_file.write_bytes(b'data')
    checksum = BackupService.calculate_checksum(str(backup_file))
    (tmp_path / f'{backup_file.name}.sha256').write_text(checksum, encoding='utf-8')
    record = BackupService.sync_filesystem()[0]

    response = admin_client.get(f'/admin/backup/download/{record.file_name}')
    assert response.status_code == 200
    assert 'attachment' in response.headers.get('Content-Disposition', '')


def test_download_backup_route_missing_file_returns_404(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    record = BackupService.create_backup(
        backup_type='manual',
        database_type='sqlite',
        file_name='missing.db',
        file_path=str(tmp_path / 'missing.db'),
        file_size=0,
        checksum='',
        status='ok',
        created_by=1,
    )
    response = admin_client.get(f'/admin/backup/download/{record.file_name}')
    assert response.status_code == 404


def test_restore_route_permission_denied(app, database, tmp_path):
    # Unauthenticated client should not be allowed to queue restores
    app.config['BACKUP_DIR'] = str(tmp_path)
    with app.test_client() as client:
        resp = client.post('/admin/backup/restore/some.db', follow_redirects=False)
        assert resp.status_code in (302, 403)
