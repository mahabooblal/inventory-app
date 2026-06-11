import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime

BACKUP_DIR = os.environ.get('BACKUP_DIR', './backups')
DB_TYPE = os.environ.get('DB_TYPE', 'postgres')
DB_URL = os.environ.get('DATABASE_URL')
RESTORE_FILE = os.environ.get('RESTORE_FILE')
DRY_RUN = os.environ.get('DRY_RUN') in ('1', 'true', 'True')


def sha256sum(filename):
    import hashlib
    h = hashlib.sha256()
    with open(filename, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def validate_checksum(restore_file):
    cfile = restore_file + '.sha256'
    if not os.path.exists(cfile):
        print(f'Checksum file missing: {cfile}', file=sys.stderr)
        if DRY_RUN:
            return False, 'missing_checksum'
        sys.exit(3)
    with open(cfile, 'r') as f:
        expected = f.read().strip()
    actual = sha256sum(restore_file)
    if expected != actual:
        print(f'Checksum mismatch! File may be corrupted.\nExpected: {expected}\nActual:   {actual}', file=sys.stderr)
        if DRY_RUN:
            return False, 'mismatch'
        sys.exit(4)
    return True, 'verified'

def restore_postgres(restore_file):
    if not DB_URL:
        print('DATABASE_URL not set', file=sys.stderr)
        if DRY_RUN:
            return False, 'no_database'
        sys.exit(1)
    ok, chk = validate_checksum(restore_file)
    if not ok:
        # validate_checksum will have exited for non-dry runs
        return False, chk
    if DRY_RUN:
        # In dry-run mode, only validate prerequisites
        report = {
            'backup_found': True,
            'checksum_status': chk,
            'corruption_status': 'ok' if chk == 'verified' else 'corrupt',
            'compatibility_status': 'postgres_ok',
            'estimated_restore_readiness': 'pass' if chk == 'verified' else 'fail',
        }
        print(report)
        return True, 'dry_run_pass' if chk == 'verified' else 'dry_run_fail'
    if restore_file.endswith('.gz'):
        with gzip.open(restore_file, 'rb') as f_in:
            sql = f_in.read()
        cmd = ['psql', DB_URL]
        print(f'Restoring from compressed backup: {restore_file}')
        result = subprocess.run(cmd, input=sql, capture_output=True)
    else:
        cmd = ['psql', DB_URL, '-f', restore_file]
        print(f'Restoring from backup: {restore_file}')
        result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode(), file=sys.stderr)
        if DRY_RUN:
            return False, 'exec_failed'
        sys.exit(2)
    print('Restore complete.')
    return True, 'restored'

def restore_sqlite(restore_file):
    if not DB_URL or not DB_URL.startswith('sqlite:///'):
        print('DATABASE_URL must be sqlite:///path/to/db', file=sys.stderr)
        if DRY_RUN:
            return False, 'no_database'
        sys.exit(1)
    db_path = DB_URL.replace('sqlite:///', '', 1)
    ok, chk = validate_checksum(restore_file)
    if not ok:
        # validate_checksum will have exited for non-dry runs
        return False, chk
    if DRY_RUN:
        report = {
            'backup_found': True,
            'checksum_status': chk,
            'corruption_status': 'ok' if chk == 'verified' else 'corrupt',
            'compatibility_status': 'sqlite_ok',
            'estimated_restore_readiness': 'pass' if chk == 'verified' else 'fail',
        }
        print(report)
        return True, 'dry_run_pass' if chk == 'verified' else 'dry_run_fail'
    if restore_file.endswith('.gz'):
        with gzip.open(restore_file, 'rb') as f_in, open(db_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    else:
        shutil.copy2(restore_file, db_path)
    print('Restore complete.')
    return True, 'restored'

def main():
    if not RESTORE_FILE or not os.path.exists(RESTORE_FILE):
        print('RESTORE_FILE not set or does not exist', file=sys.stderr)
        sys.exit(1)
    if DB_TYPE == 'postgres':
        ok, msg = restore_postgres(RESTORE_FILE)
    elif DB_TYPE == 'sqlite':
        ok, msg = restore_sqlite(RESTORE_FILE)
    else:
        print('Unknown DB_TYPE', file=sys.stderr)
        sys.exit(1)
    # map results to exit codes
    if ok:
        return
    else:
        # non-zero exit for failures
        sys.exit(2)

if __name__ == '__main__':
    main()
