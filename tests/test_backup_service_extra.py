import os
from datetime import datetime, timedelta

import pytest
from app.models import BackupRecord
from app.repositories.backup_repository import BackupRepository
from app.services.backup_service import BackupService


def test_safe_backup_path_rejects_invalid_filename(app, tmp_path):
    app.config['BACKUP_DIR'] = str(tmp_path)

    with pytest.raises(ValueError):
        BackupService.safe_backup_path('../etc/passwd')

    with pytest.raises(ValueError):
        BackupService.safe_backup_path('not_a_backup.txt')


def test_run_backup_failure_creates_failed_record(app, database, tmp_path, monkeypatch):
    app.config['BACKUP_DIR'] = str(tmp_path)
    source_db = tmp_path / 'source.db'
    source_db.write_text('content', encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{source_db}')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')
    monkeypatch.setenv('DB_TYPE', 'sqlite')

    fake_result = type('R', (), {'returncode': 2, 'stdout': '', 'stderr': 'failure'})
    monkeypatch.setattr('app.services.backup_service.subprocess.run', lambda *args, **kwargs: fake_result)

    ok, output = BackupService.run_backup(backup_type='manual', created_by=1)
    assert ok is False
    assert 'failure' in output

    failed = BackupRecord.query.filter_by(status='failed').first()
    assert failed is not None


def test_verify_backup_missing_file_marks_missing(app, database, tmp_path):
    record = BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='missing.db',
        file_path=str(tmp_path / 'missing.db'),
        file_size=0,
        checksum='',
        status='ok',
        created_at=datetime.utcnow(),
        retention_until=datetime.utcnow() + timedelta(days=1),
        created_by=1,
    )

    updated = BackupService.verify_backup(record.id)
    assert updated.status == 'missing'
    assert updated.verification_status == 'missing'


def test_restore_backup_failure_logs_failed(app, database, tmp_path):
    record = BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='backup.db',
        file_path=str(tmp_path / 'backup.db'),
        file_size=0,
        checksum='',
        status='ok',
        created_at=datetime.utcnow(),
        retention_until=datetime.utcnow() + timedelta(days=1),
        created_by=1,
    )

    updated = BackupService.restore_backup(record.id, restored_by=1, restore_status='failed', notes='broken')
    assert updated.restore_status == 'failed'
    assert 'broken' in updated.notes


def test_reconcile_backups_detects_checksum_mismatch(app, database, tmp_path):
    backup_file = tmp_path / 'backup.db'
    backup_file.write_bytes(b'abc')
    (tmp_path / 'backup.db.sha256').write_text('deadbeef', encoding='utf-8')

    record = BackupRepository.create(
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

    result = BackupService.reconcile_backups(backup_dir=str(tmp_path))
    assert record in result['checksum_mismatches']
    assert result['missing_files'] == []
