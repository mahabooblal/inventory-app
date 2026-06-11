import os
import sys
import subprocess
import shutil
from datetime import datetime, timedelta
import gzip
import glob

BACKUP_DIR = os.environ.get('BACKUP_DIR', './backups')
DB_TYPE = os.environ.get('DB_TYPE', 'postgres')  # 'postgres' or 'sqlite'
DB_URL = os.environ.get('DATABASE_URL')
RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '7'))
COMPRESS = os.environ.get('BACKUP_COMPRESS', '1') in {'1', 'true', 'yes'}

os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_postgres():
    if not DB_URL:
        print('DATABASE_URL not set', file=sys.stderr)
        sys.exit(1)
    dt = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    fname = f'pg_backup_{dt}.sql'
    fpath = os.path.join(BACKUP_DIR, fname)
    cmd = [
        'pg_dump', DB_URL, '-F', 'p', '-f', fpath
    ]
    print(f'Running: {" ".join(cmd)}')
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode(), file=sys.stderr)
        sys.exit(2)
    if COMPRESS:
        with open(fpath, 'rb') as f_in, gzip.open(fpath + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(fpath)
        fpath += '.gz'
    # Generate checksum
    checksum = sha256sum(fpath)
    with open(fpath + '.sha256', 'w') as f:
        f.write(checksum)
    print(f'Backup complete: {fpath} (sha256: {checksum})')
    return fpath

def backup_sqlite():
    if not DB_URL or not DB_URL.startswith('sqlite:///'):
        print('DATABASE_URL must be sqlite:///path/to/db', file=sys.stderr)
        sys.exit(1)
    db_path = DB_URL.replace('sqlite:///', '', 1)
    dt = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    fname = f'sqlite_backup_{dt}.db'
    fpath = os.path.join(BACKUP_DIR, fname)
    shutil.copy2(db_path, fpath)
    if COMPRESS:
        with open(fpath, 'rb') as f_in, gzip.open(fpath + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(fpath)
        fpath += '.gz'
    # Generate checksum
    checksum = sha256sum(fpath)
    with open(fpath + '.sha256', 'w') as f:
        f.write(checksum)
    print(f'Backup complete: {fpath} (sha256: {checksum})')
    return fpath

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

def cleanup_old_backups():
    now = datetime.utcnow()
    for f in glob.glob(os.path.join(BACKUP_DIR, '*')):
        try:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(f))
            if now - mtime > timedelta(days=RETENTION_DAYS):
                os.remove(f)
                print(f'Removed old backup: {f}')
        except Exception as e:
            print(f'Error removing {f}: {e}', file=sys.stderr)

def main():
    if DB_TYPE == 'postgres':
        backup_postgres()
    elif DB_TYPE == 'sqlite':
        backup_sqlite()
    else:
        print('Unknown DB_TYPE', file=sys.stderr)
        sys.exit(1)
    cleanup_old_backups()

if __name__ == '__main__':
    main()
