from datetime import datetime, timedelta

from app.models import BackupRecord
from app.repositories.backup_repository import BackupRepository
from app.services.backup_service import BackupService
from app.tasks.backup_tasks import BackupTasks


def test_scheduled_backup_invokes_run_backup(monkeypatch):
    monkeypatch.setattr('app.tasks.backup_tasks.BackupService.run_backup', lambda backup_type, created_by: (True, 'ok'))

    ok, output = BackupTasks.scheduled_backup(user_id=1)
    assert ok is True
    assert output == 'ok'


def test_retention_cleanup_deletes_expired_records(app, database, tmp_path):
    backup_file = tmp_path / 'backup.db'
    backup_file.write_bytes(b'old')
    expired = BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='expired.db',
        file_path=str(backup_file),
        file_size=backup_file.stat().st_size,
        checksum='abc',
        status='ok',
        created_at=datetime.utcnow(),
        retention_until=datetime.utcnow() - timedelta(days=1),
        created_by=1,
    )

    count = BackupTasks.retention_cleanup()
    assert count == 1
    assert BackupRepository.get_by_id(expired.id) is None


def test_verify_all_backups_calls_verify_backup(monkeypatch, app, database, tmp_path):
    backup_file = tmp_path / 'backup.db'
    backup_file.write_bytes(b'x')
    BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='backup.db',
        file_path=str(backup_file),
        file_size=backup_file.stat().st_size,
        checksum='abc',
        status='ok',
        created_at=datetime.utcnow(),
        retention_until=datetime.utcnow() + timedelta(days=1),
        created_by=1,
    )

    monkeypatch.setattr('app.tasks.backup_tasks.BackupService.verify_backup', lambda record_id: 'verified')
    verified = BackupTasks.verify_all_backups()
    assert verified == ['verified']


def test_reconcile_backups_returns_mismatch_and_orphan_files(app, database, tmp_path):
    backup_file = tmp_path / 'backup.db'
    backup_file.write_bytes(b'abc')
    (tmp_path / 'backup.db.sha256').write_text('deadbeef', encoding='utf-8')
    BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='backup.db',
        file_path=str(backup_file),
        file_size=backup_file.stat().st_size,
        checksum='deadbeef',
        status='ok',
        created_at=datetime.utcnow(),
        retention_until=datetime.utcnow() + timedelta(days=1),
        created_by=1,
    )
    orphan_file = tmp_path / 'orphan.db'
    orphan_file.write_bytes(b'orphan')

    result = BackupTasks.reconcile_backups(backup_dir=str(tmp_path))
    assert 'orphan.db' in result['orphan_files']
    assert len(result['checksum_mismatches']) == 1
