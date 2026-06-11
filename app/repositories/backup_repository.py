import os

from app import db
from app.models.backup_record import BackupRecord
from datetime import datetime

BACKUP_EXTENSIONS = ('.sql', '.sql.gz', '.db', '.db.gz')

class BackupRepository:
    @staticmethod
    def create(**kwargs):
        record = BackupRecord(**kwargs)
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def update(record_id, **kwargs):
        record = BackupRecord.query.get(record_id)
        if not record:
            return None
        for k, v in kwargs.items():
            setattr(record, k, v)
        db.session.commit()
        return record

    @staticmethod
    def get_by_id(record_id):
        return BackupRecord.query.get(record_id)

    @staticmethod
    def get_by_filename(file_name):
        return BackupRecord.query.filter_by(file_name=file_name).first()

    @staticmethod
    def get_latest():
        return BackupRecord.query.order_by(BackupRecord.created_at.desc()).first()

    @staticmethod
    def get_all(order_by='created_at', desc=True):
        q = BackupRecord.query
        if not hasattr(BackupRecord, order_by):
            order_by = 'created_at'
        if desc:
            q = q.order_by(getattr(BackupRecord, order_by).desc())
        else:
            q = q.order_by(getattr(BackupRecord, order_by))
        return q.all()

    @staticmethod
    def get_paginated(page=1, per_page=20, filters=None, sort_by='created_at', desc=True):
        q = BackupRecord.query
        if filters:
            for attr, value in filters.items():
                if hasattr(BackupRecord, attr):
                    q = q.filter(getattr(BackupRecord, attr) == value)
        if not hasattr(BackupRecord, sort_by):
            sort_by = 'created_at'
        if desc:
            q = q.order_by(getattr(BackupRecord, sort_by).desc())
        else:
            q = q.order_by(getattr(BackupRecord, sort_by))
        return q.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_by_status(status):
        return BackupRecord.query.filter_by(status=status).all()

    @staticmethod
    def get_by_verification_status(verification_status):
        return BackupRecord.query.filter_by(verification_status=verification_status).all()

    @staticmethod
    def find_missing_files():
        return [r for r in BackupRecord.query.all() if r.file_path and not os.path.exists(r.file_path)]

    @staticmethod
    def find_orphan_files(backup_dir):
        if not os.path.isdir(backup_dir):
            return []
        db_files = {r.file_name for r in BackupRecord.query.all()}
        fs_files = {
            name for name in os.listdir(backup_dir)
            if name.endswith(BACKUP_EXTENSIONS) and os.path.isfile(os.path.join(backup_dir, name))
        }
        return sorted(fs_files - db_files)

    @staticmethod
    def delete(record_id):
        record = BackupRecord.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            return True
        return False
