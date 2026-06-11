from datetime import datetime, timedelta

from app import db
from app.models import BackupRecord
from app.services.backup_service import BackupService
from app.tasks.backup_tasks import BackupTasks


def write_backup(path, content=b'backup-data'):
    path.write_bytes(content)
    checksum = BackupService.calculate_checksum(str(path))
    (path.parent / f'{path.name}.sha256').write_text(checksum, encoding='utf-8')
    return checksum


def test_backup_service_syncs_and_verifies_filesystem_backup(app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = tmp_path / 'sqlite_backup_20260531_120000.db'
    checksum = write_backup(backup_file)

    records = BackupService.sync_filesystem()

    assert len(records) == 1
    record = records[0]
    assert record.file_name == backup_file.name
    assert record.database_type == 'sqlite'
    assert record.checksum == checksum
    assert record.status == 'ok'

    verified = BackupService.verify_backup(record.id)
    assert verified.verification_status == 'verified'
    assert verified.status == 'ok'


def test_backup_reconciliation_reports_missing_orphan_and_checksum_mismatch(app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    known_file = tmp_path / 'sqlite_backup_20260531_120000.db'
    write_backup(known_file, b'original')
    known_record = BackupService.sync_filesystem()[0]

    known_file.write_bytes(b'changed')
    missing_record = BackupRecord(
        backup_type='manual',
        database_type='sqlite',
        file_name='sqlite_backup_missing.db',
        file_path=str(tmp_path / 'sqlite_backup_missing.db'),
        file_size=10,
        checksum='abc',
        status='ok',
        created_at=datetime.utcnow(),
    )
    db.session.add(missing_record)
    db.session.commit()

    orphan_file = tmp_path / 'sqlite_backup_orphan.db'
    write_backup(orphan_file, b'orphan')

    result = BackupService.reconcile_backups()

    assert missing_record in result['missing_files']
    assert orphan_file.name in result['orphan_files']
    assert known_record in result['checksum_mismatches']


def test_backup_retention_cleanup_removes_expired_record_and_files(app, database, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = tmp_path / 'sqlite_backup_20260531_120000.db'
    checksum = write_backup(backup_file)
    record = BackupRecord(
        backup_type='scheduled',
        database_type='sqlite',
        file_name=backup_file.name,
        file_path=str(backup_file),
        file_size=backup_file.stat().st_size,
        checksum=checksum,
        status='ok',
        created_at=datetime.utcnow() - timedelta(days=10),
        retention_until=datetime.utcnow() - timedelta(days=1),
    )
    db.session.add(record)
    db.session.commit()

    deleted = BackupTasks.retention_cleanup()

    assert deleted == 1
    assert BackupRecord.query.count() == 0
    assert not backup_file.exists()
    assert not (tmp_path / f'{backup_file.name}.sha256').exists()


def test_backup_status_endpoint_uses_backup_records(admin_client, app, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)
    backup_file = tmp_path / 'sqlite_backup_20260531_120000.db'
    checksum = write_backup(backup_file)
    BackupService.sync_filesystem()

    response = admin_client.get('/backup/status')

    assert response.status_code == 200
    data = response.get_json()
    assert data['health'] == 'ok'
    assert data['last_checksum'] == checksum
    assert data['history'][0]['filename'] == backup_file.name
