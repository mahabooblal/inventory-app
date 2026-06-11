import subprocess
from pathlib import Path


def test_restore_script_dry_run_sqlite_success(tmp_path, monkeypatch, capsys):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('restored content', encoding='utf-8')
    checksum = subprocess.run([
        'python', '-c', 'import hashlib,sys; h=hashlib.sha256(); h.update(open(sys.argv[1],"rb").read()); print(h.hexdigest())',
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
    monkeypatch.setenv('DRY_RUN', '1')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    module = __import__('importlib.util')
    import importlib.util
    spec = importlib.util.spec_from_file_location(script.stem, script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # should not raise SystemExit for dry-run success
    mod.main()
    captured = capsys.readouterr()
    assert 'checksum_status' in captured.out


def test_restore_script_dry_run_sqlite_invalid_checksum(tmp_path, monkeypatch):
    backup_file = tmp_path / 'restore.db'
    backup_file.write_text('bad content', encoding='utf-8')
    (tmp_path / 'restore.db.sha256').write_text('deadbeef', encoding='utf-8')
    target_db = tmp_path / 'target.db'
    target_db.write_text('old content', encoding='utf-8')

    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{target_db}')
    monkeypatch.setenv('RESTORE_FILE', str(backup_file))
    monkeypatch.setenv('DRY_RUN', '1')

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'restore.py'
    import importlib.util
    spec = importlib.util.spec_from_file_location(script.stem, script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import pytest
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 2
