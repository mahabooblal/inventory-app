from datetime import datetime, timedelta

from app.repositories.backup_repository import BackupRepository


def test_backup_repository_crud_and_queries(app, database, tmp_path):
    sample_file = tmp_path / 'backup.db'
    sample_file.write_bytes(b'hello')
    now = datetime.utcnow()

    record = BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='backup.db',
        file_path=str(sample_file),
        file_size=sample_file.stat().st_size,
        checksum='abc',
        status='ok',
        created_at=now,
        retention_until=now + timedelta(days=1),
        created_by=1,
    )

    assert BackupRepository.get_by_id(record.id).id == record.id
    assert BackupRepository.get_by_filename('backup.db').id == record.id
    assert BackupRepository.get_latest().id == record.id
    assert BackupRepository.get_all()[0].id == record.id
    assert BackupRepository.get_paginated(page=1, per_page=1).items[0].id == record.id
    assert BackupRepository.get_by_status('ok')[0].id == record.id
    assert BackupRepository.get_by_verification_status(record.verification_status)[0].id == record.id
    assert BackupRepository.find_missing_files() == []
    assert BackupRepository.find_orphan_files(str(tmp_path)) == []

    missing_file = tmp_path / 'missing.db'
    missing_record = BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='missing.db',
        file_path=str(missing_file),
        file_size=0,
        checksum='',
        status='ok',
        created_at=now,
        retention_until=now + timedelta(days=1),
        created_by=1,
    )
    assert BackupRepository.find_missing_files() == [missing_record]

    orphan = tmp_path / 'orphan.db'
    orphan.write_text('orphan', encoding='utf-8')
    orphan_files = BackupRepository.find_orphan_files(str(tmp_path))
    assert 'orphan.db' in orphan_files

    assert BackupRepository.delete(record.id) is True
    assert BackupRepository.get_by_id(record.id) is None
    assert BackupRepository.delete(999999) is False


def test_backup_repository_pagination_filters_and_sorting(app, database, tmp_path):
    sample_file = tmp_path / 'backup2.db'
    sample_file.write_bytes(b'world')
    now = datetime.utcnow()
    BackupRepository.create(
        backup_type='manual',
        database_type='sqlite',
        file_name='backup2.db',
        file_path=str(sample_file),
        file_size=sample_file.stat().st_size,
        checksum='abc',
        status='ok',
        created_at=now,
        retention_until=now + timedelta(days=1),
        created_by=1,
    )

    paginated = BackupRepository.get_paginated(page=1, per_page=1, filters={'status': 'ok'}, sort_by='file_name', desc=False)
    assert paginated.items[0].file_name == 'backup2.db'
    assert BackupRepository.get_paginated(page=1, per_page=1, sort_by='invalid_field').items
