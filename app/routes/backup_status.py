from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from app.services.backup_service import BackupService
from app.utils.permissions import roles_required

bp = Blueprint('backup_status', __name__)


def serialize_backup(record):
    return {
        'id': record.id,
        'filename': record.file_name,
        'timestamp': record.created_at.isoformat() + 'Z' if record.created_at else None,
        'size': record.file_size,
        'type': record.database_type,
        'checksum': record.checksum,
        'status': record.status,
        'verification_status': record.verification_status,
    }


@bp.route('/backup/status')
@login_required
@roles_required('admin')
def backup_status():
    # Admin-only detailed status
    BackupService.sync_filesystem()
    backups = BackupService.get_all_backups()
    last = backups[0] if backups else None
    failed = [b for b in backups if b.status != 'ok']
    return jsonify({
        'last_successful': last.created_at.isoformat() + 'Z' if last and last.status == 'ok' and last.created_at else None,
        'last_size': last.file_size if last else None,
        'last_type': last.database_type if last else None,
        'last_checksum': last.checksum if last else None,
        'health': 'ok' if last and last.status == 'ok' else 'degraded',
        'failed_backups': [serialize_backup(b) for b in failed],
        'history': [serialize_backup(b) for b in backups[:10]],
    })


@bp.route('/backup/status/summary')
def backup_status_summary():
    # Metrics-safe public summary, no sensitive metadata
    BackupService.sync_filesystem()
    backups = BackupService.get_all_backups()
    last = backups[0] if backups else None
    failed = [b for b in backups if b.status != 'ok']
    return jsonify({
        'last_successful': last.created_at.isoformat() + 'Z' if last and last.status == 'ok' and last.created_at else None,
        'health': 'ok' if last and last.status == 'ok' else 'degraded',
        'total_backups': len(backups),
        'failed_count': len(failed),
    })
