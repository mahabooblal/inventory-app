import importlib.util
import os
import subprocess
import sys
import tempfile
import runpy
import pytest
from pathlib import Path


def load_script_module(script_path):
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backup_script_sqlite_success(tmp_path):
    db_file = tmp_path / 'source.db'
    db_file.write_text('original content', encoding='utf-8')
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    env = os.environ.copy()
    env.update({
        'BACKUP_DIR': str(backup_dir),
        'DB_TYPE': 'sqlite',
        'DATABASE_URL': f'sqlite:///{db_file}',
        'BACKUP_COMPRESS': '0',
        'BACKUP_RETENTION_DAYS': '7',
    })
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Backup complete:' in result.stdout
    files = list(backup_dir.glob('sqlite_backup_*.db'))
    assert len(files) == 1
    assert (backup_dir / f'{files[0].name}.sha256').exists()


def test_backup_script_missing_dburl_fails(tmp_path):
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    env = os.environ.copy()
    env.update({
        'BACKUP_DIR': str(backup_dir),
        'DB_TYPE': 'sqlite',
        'BACKUP_COMPRESS': '0',
    })
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert 'DATABASE_URL must be sqlite:///path/to/db' in result.stderr


def test_backup_script_retention_cleanup_removes_old_files(tmp_path):
    db_file = tmp_path / 'source.db'
    db_file.write_text('original content', encoding='utf-8')
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    old = backup_dir / 'old.db'
    old.write_text('old', encoding='utf-8')
    os.utime(old, (0, 0))
    env = os.environ.copy()
    env.update({
        'BACKUP_DIR': str(backup_dir),
        'DB_TYPE': 'sqlite',
        'DATABASE_URL': f'sqlite:///{db_file}',
        'BACKUP_COMPRESS': '0',
        'BACKUP_RETENTION_DAYS': '0',
    })
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert not old.exists()


def test_restore_script_sqlite_success(tmp_path):
    source_db = tmp_path / 'source.db'
    source_db.write_text('restored content', encoding='utf-8')
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.db.sha256').write_text(expected, encoding='utf-8')
    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')
    env = os.environ.copy()
    env.update({
        'BACKUP_DIR': str(tmp_path),
        'DB_TYPE': 'sqlite',
        'DATABASE_URL': f'sqlite:///{target_db}',
        'RESTORE_FILE': str(backup_file),
    })
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Restore complete.' in result.stdout
    assert target_db.read_text(encoding='utf-8') == 'restored content'


def test_restore_script_invalid_checksum(tmp_path):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('bad content', encoding='utf-8')
    (tmp_path / 'restore.db.sha256').write_text('deadbeef', encoding='utf-8')
    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')
    env = os.environ.copy()
    env.update({
        'BACKUP_DIR': str(tmp_path),
        'DB_TYPE': 'sqlite',
        'DATABASE_URL': f'sqlite:///{target_db}',
        'RESTORE_FILE': str(backup_file),
    })
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 4
    assert 'Checksum mismatch' in result.stderr


def test_restore_script_missing_checksum(tmp_path):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('bad content', encoding='utf-8')
    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')
    env = os.environ.copy()
    env.update({
        'BACKUP_DIR': str(tmp_path),
        'DB_TYPE': 'sqlite',
        'DATABASE_URL': f'sqlite:///{target_db}',
        'RESTORE_FILE': str(backup_file),
    })
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 3
    assert 'Checksum file missing' in result.stderr


def test_backup_script_module_sqlite_main(tmp_path, monkeypatch):
    source_db = tmp_path / 'source.db'
    source_db.write_text('original content', encoding='utf-8')
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()

    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{source_db}')
    monkeypatch.setenv('BACKUP_COMPRESS', '0')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)
    module.main()

    files = list(backup_dir.glob('sqlite_backup_*.db'))
    assert len(files) == 1
    assert (backup_dir / f'{files[0].name}.sha256').exists()


def test_restore_script_module_sqlite_main_success(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.db.sha256').write_text(expected, encoding='utf-8')
    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{target_db}')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)
    module.main()

    assert target_db.read_text(encoding='utf-8') == 'restored content'


def test_backup_script_module_sqlite_main_with_compress(tmp_path, monkeypatch):
    source_db = tmp_path / 'source.db'
    source_db.write_text('original content', encoding='utf-8')
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()

    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{source_db}')
    monkeypatch.setenv('BACKUP_COMPRESS', '1')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)
    module.main()

    files = list(backup_dir.glob('sqlite_backup_*.db.gz'))
    assert len(files) == 1
    assert (backup_dir / f'{files[0].name}.sha256').exists()


def test_backup_script_module_postgres_main(tmp_path, monkeypatch):
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/testdb')
    monkeypatch.setenv('BACKUP_COMPRESS', '0')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)

    def fake_run(cmd, capture_output=False, text=False, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_text('pgdump', encoding='utf-8')
        return type('R', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()

    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    module.main()

    assert any(p.name.startswith('pg_backup_') and p.suffix == '.sql' for p in backup_dir.iterdir())


def test_backup_script_module_postgres_main_compress_success(tmp_path, monkeypatch):
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/testdb')
    monkeypatch.setenv('BACKUP_COMPRESS', '1')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)

    def fake_run(cmd, capture_output=False, text=False, **kwargs):
        output_path = cmd[-1]
        Path(output_path).write_bytes(b'pgdump')
        return type('R', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()

    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    module.main()

    assert any(p.name.startswith('pg_backup_') and p.suffix == '.gz' for p in backup_dir.iterdir())
    assert any(p.name.endswith('.sha256') for p in backup_dir.iterdir())


def test_backup_script_module_postgres_main_failure_exits(tmp_path, monkeypatch):
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/testdb')
    monkeypatch.setenv('BACKUP_COMPRESS', '0')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)

    def fake_run(cmd, capture_output=False, text=False, **kwargs):
        return type('R', (), {'returncode': 1, 'stdout': b'', 'stderr': b'pg_dump failed'})()

    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert excinfo.value.code == 2


def test_backup_script_module_postgres_no_database_url_exits(tmp_path, monkeypatch):
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('BACKUP_COMPRESS', '0')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.backup_postgres()
    assert excinfo.value.code == 1


def test_backup_script_module_cleanup_old_backups_handles_errors(tmp_path, monkeypatch):
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    old = backup_dir / 'old.db'
    old.write_text('old content', encoding='utf-8')
    os.utime(old, (0, 0))

    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '0')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)
    module.RETENTION_DAYS = 0

    def broken_remove(path):
        raise OSError('unable to delete')

    monkeypatch.setattr(module.os, 'remove', broken_remove)
    module.cleanup_old_backups()


def test_backup_script_module_cleanup_old_backups_removes_file(tmp_path, monkeypatch):
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    old = backup_dir / 'old.db'
    old.write_text('old content', encoding='utf-8')
    os.utime(old, (0, 0))

    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '0')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)
    module.RETENTION_DAYS = 0

    module.cleanup_old_backups()
    assert not old.exists()


def test_backup_script_module_sqlite_missing_database_url_exits(tmp_path, monkeypatch):
    source_db = tmp_path / 'source.db'
    source_db.write_text('original content', encoding='utf-8')
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()

    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('BACKUP_COMPRESS', '0')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.backup_sqlite()
    assert excinfo.value.code == 1


def test_backup_script_module_unknown_db_type_exits(tmp_path, monkeypatch):
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'unknown')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///does/not/matter.db')
    monkeypatch.setenv('BACKUP_COMPRESS', '0')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert excinfo.value.code == 1


def test_backup_script_main_entrypoint_runs_under_dunder_main(tmp_path, monkeypatch):
    source_db = tmp_path / 'source.db'
    source_db.write_text('original content', encoding='utf-8')
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()

    monkeypatch.setenv('BACKUP_DIR', str(backup_dir))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{source_db}')
    monkeypatch.setenv('BACKUP_COMPRESS', '0')
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '7')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backup.py'
    runpy.run_path(str(script), run_name='__main__')

    assert any(backup_dir.glob('sqlite_backup_*.db'))


def test_restore_script_module_postgres_main_success(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.sql'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.sql.sha256').write_text(expected, encoding='utf-8')
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/testdb')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    def fake_run(cmd, input=None, capture_output=False, **kwargs):
        return type('R', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()

    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    module.main()


def test_restore_script_module_sqlite_main_gz_success(tmp_path, monkeypatch):
    import gzip

    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')
    raw_file = tmp_path / 'restore.db'
    raw_file.write_text('restored content', encoding='utf-8')
    compressed_file = tmp_path / 'restore.db.gz'
    with gzip.open(compressed_file, 'wb') as f_out:
        f_out.write(raw_file.read_bytes())
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(compressed_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.db.gz.sha256').write_text(expected, encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{target_db}')
    monkeypatch.setenv('RESTORE_FILE', str(compressed_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)
    module.main()

    assert target_db.read_text(encoding='utf-8') == 'restored content'


def test_restore_script_module_sqlite_main_invalid_checksum(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('bad content', encoding='utf-8')
    (tmp_path / 'restore.db.sha256').write_text('deadbeef', encoding='utf-8')
    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{target_db}')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert excinfo.value.code == 4


def test_restore_script_module_sqlite_main_missing_checksum(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('bad content', encoding='utf-8')
    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{target_db}')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert excinfo.value.code == 3


def test_restore_script_module_postgres_main_gz_success(tmp_path, monkeypatch):
    import gzip

    backup_file = tmp_path / 'restore.sql'
    raw_contents = b'restored content'
    backup_file.write_bytes(raw_contents)
    compressed_file = tmp_path / 'restore.sql.gz'
    with gzip.open(compressed_file, 'wb') as f_out:
        f_out.write(raw_contents)

    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(compressed_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.sql.gz.sha256').write_text(expected, encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/testdb')
    monkeypatch.setenv('RESTORE_FILE', str(compressed_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    def fake_run(cmd, input=None, capture_output=False, **kwargs):
        return type('R', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()

    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    module.main()


def test_restore_script_module_postgres_missing_db_url_exits(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.sql'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.sql.sha256').write_text(expected, encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.restore_postgres(str(backup_file))
    assert excinfo.value.code == 1


def test_restore_script_module_postgres_failure_exits(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.sql'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.sql.sha256').write_text(expected, encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'postgres')
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/testdb')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    def fake_run(cmd, input=None, capture_output=False, **kwargs):
        return type('R', (), {'returncode': 1, 'stdout': b'', 'stderr': b'psql failed'})()

    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    with pytest.raises(SystemExit) as excinfo:
        module.restore_postgres(str(backup_file))
    assert excinfo.value.code == 2


def test_restore_script_module_sqlite_invalid_database_url_exits(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.db.sha256').write_text(expected, encoding='utf-8')

    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', 'not-a-sqlite-url')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.restore_sqlite(str(backup_file))
    assert excinfo.value.code == 1


def test_restore_script_module_main_missing_restore_file_exits(tmp_path, monkeypatch):
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "target.db"}')
    monkeypatch.setenv('RESTORE_FILE', str(tmp_path / 'missing.db'))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert excinfo.value.code == 1


def test_restore_script_module_main_unknown_db_type_exits(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.db.sha256').write_text(expected, encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'unknown')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///target.db')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = load_script_module(script)

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert excinfo.value.code == 1


def test_restore_script_main_entrypoint_runs_under_dunder_main(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        sys.executable,
        '-c',
        'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
        str(backup_file),
    ], capture_output=True, text=True)
    expected = checksum.stdout.strip()
    (tmp_path / 'restore.db.sha256').write_text(expected, encoding='utf-8')

    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{target_db}')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    runpy.run_path(str(script), run_name='__main__')

    assert target_db.read_text(encoding='utf-8') == 'restored content'
