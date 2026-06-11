from app import db
from app.models.types import UTCDateTime
from datetime import datetime

class BackupRecord(db.Model):
    __tablename__ = 'backup_records'
    id = db.Column(db.Integer, primary_key=True)
    backup_type = db.Column(db.String(32), nullable=False)  # e.g. 'manual', 'scheduled'
    database_type = db.Column(db.String(16), nullable=False)  # 'postgres' or 'sqlite'
    file_name = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    checksum = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False, index=True)  # 'ok', 'failed', 'corrupt', etc.
    created_at = db.Column(UTCDateTime(), default=datetime.utcnow, index=True)
    retention_until = db.Column(UTCDateTime(), nullable=True)
    verified_at = db.Column(UTCDateTime(), nullable=True)
    verification_status = db.Column(db.String(32), nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    restored_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    restore_timestamp = db.Column(UTCDateTime(), nullable=True)
    restore_status = db.Column(db.String(32), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    creator = db.relationship('User', foreign_keys=[created_by], backref='backups_created')
    restorer = db.relationship('User', foreign_keys=[restored_by], backref='backups_restored')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
