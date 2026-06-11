import os
from datetime import datetime, timedelta

from app import db
from app.models import BackupRecord, AuditLog
from app.services.backup_service import BackupService


def create_backup_file(tmp_path, name='sqlite_backup_test.db', content=b'data'):
    f = tmp_path / name
    f.write_bytes(content)
    checksum = BackupService.calculate_checksum(str(f))
    (tmp_path / f'{f.name}.sha256').write_text(checksum, encoding='utf-8')
    return f, checksum


def test_dashboard_and_history_pagination(admin_client, app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    # create 15 backups to exercise pagination (PAGE_SIZE=10)
    for i in range(15):
        create_backup_file(tmp_path, name=f'sqlite_backup_{i}.db')
    records = BackupService.sync_filesystem()
    assert len(records) == 15

    # Dashboard route should render successfully for admin
    resp = admin_client.get('/admin/backup/')
    assert resp.status_code == 200

    # Page 2 should be accessible
    resp2 = admin_client.get('/admin/backup/?page=2')
    assert resp2.status_code == 200


def test_dashboard_empty_state_and_status_endpoints(app, database, tmp_path, admin_user):
    app.config['BACKUP_DIR'] = str(tmp_path)
    with app.test_client() as client:
        login_resp = client.post('/auth/login', data={'username': admin_user.username, 'password': 'password'})
        assert login_resp.status_code in (200, 302)
        resp = client.get('/admin/backup/')
        assert resp.status_code == 200
        assert b'No backups' in resp.data or b'backup' in resp.data

        status = client.get('/backup/status')
        assert status.status_code == 200

        # Ensure the next anonymous client is truly unauthenticated.
        client.get('/auth/logout', follow_redirects=True)

    summary = app.test_client().get('/backup/status/summary')
    assert summary.status_code == 200
    data = summary.get_json()
    assert 'health' in data

    unauthorized = app.test_client().get('/backup/status', follow_redirects=False)
    assert unauthorized.status_code in (302, 403)
    if unauthorized.status_code == 302:
        assert '/auth/login' in unauthorized.headers.get('Location', '')


def test_backup_create_audit_is_logged(app, database, admin_user, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    file_path = tmp_path / 'manual.db'
    file_path.write_text('x', encoding='utf-8')
    record = BackupService.create_backup(
        backup_type='manual',
        database_type='sqlite',
        file_name='manual.db',
        file_path=str(file_path),
        file_size=1,
        checksum='abc',
        created_by=admin_user,
    )
    assert record is not None
    audit = AuditLog.query.filter_by(action='BACKUP_CREATED', target=str(record.id)).first()
    assert audit is not None
    assert audit.user_id == admin_user.id
    assert audit.username == admin_user.username
    assert audit.ip_address == 'system'
    assert audit.timestamp is not None
    assert audit.result == 'ok'


def test_download_delete_verify_manual_backup_and_audit(app, database, tmp_path, admin_user, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    f, checksum = create_backup_file(tmp_path)
    rec = BackupService.sync_filesystem()[0]

    with app.test_client() as client:
        login_resp = client.post('/auth/login', data={'username': admin_user.username, 'password': 'password'})
        assert login_resp.status_code in (200, 302)

        # Download
        dl = client.get(f'/admin/backup/download/{rec.file_name}')
        assert dl.status_code == 200
        dl.close()
        a = AuditLog.query.filter_by(action='backup_download').first()
        assert a is not None
        assert str(rec.file_name) in a.target

        # Verify
        resp = client.post(f'/admin/backup/verify/{rec.file_name}', follow_redirects=True)
        assert resp.status_code == 200
        updated = BackupRecord.query.get(rec.id)
        assert updated.verification_status == 'verified'
        av = AuditLog.query.filter_by(action='BACKUP_VERIFIED').first()
        assert av is not None

        # Delete
        resp = client.post(f'/admin/backup/delete/{rec.file_name}')
        assert resp.status_code in (302, 303)

    assert not (tmp_path / rec.file_name).exists()
    assert not (tmp_path / f'{rec.file_name}.sha256').exists()
    assert BackupRecord.query.get(rec.id) is None
    ad = AuditLog.query.filter_by(action='BACKUP_DELETED').first()
    assert ad is not None

    def fake_run(backup_type='manual', created_by=None):
        return True, BackupService.create_backup(backup_type=backup_type, file_name='manual.db', file_path=str(tmp_path/'manual.db'), file_size=1, checksum='abc', created_by=created_by)

    monkeypatch.setattr('app.services.backup_service.BackupService.run_backup', fake_run)
    with app.test_client() as client:
        client.post('/auth/login', data={'username': admin_user.username, 'password': 'password'})
        resp = client.post('/admin/backup/run', follow_redirects=True)
        assert resp.status_code == 200
    assert BackupRecord.query.filter_by(file_name='manual.db').first() is not None
    created_audit = AuditLog.query.filter_by(action='BACKUP_CREATED').first()
    assert created_audit is not None
