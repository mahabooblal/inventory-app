"""Maintenance and cleanup background tasks."""

from app.tasks.runner import register_task
from datetime import datetime, timedelta


@register_task('cleanup_audit_logs', max_retries=1)
def cleanup_audit_logs_task(days_to_keep: int = 90):
    """Clean up old audit logs."""
    from app import db
    from app.models import AuditLog

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    deleted = db.session.query(AuditLog).filter(AuditLog.created_at < cutoff_date).delete()
    db.session.commit()
    return {'deleted_count': deleted, 'cutoff_date': cutoff_date.isoformat()}


@register_task('cleanup_expired_tokens', max_retries=1)
def cleanup_expired_tokens_task():
    """Clean up expired authentication tokens."""
    from app import db
    from app.models import Token

    now = datetime.utcnow()
    deleted = db.session.query(Token).filter(Token.expires_at < now).delete()
    db.session.commit()
    return {'deleted_count': deleted, 'current_time': now.isoformat()}


@register_task('cleanup_temporary_files', max_retries=1)
def cleanup_temporary_files_task(days_to_keep: int = 7):
    """Clean up temporary export/report files older than specified days."""
    import os
    import shutil
    from pathlib import Path

    temp_dir = Path('/tmp/inventory_app_exports') if os.name != 'nt' else Path('C:\\Temp\\inventory_app_exports')
    if not temp_dir.exists():
        return {'deleted_count': 0, 'message': 'Temp directory does not exist'}

    cutoff_time = (datetime.utcnow() - timedelta(days=days_to_keep)).timestamp()
    deleted_count = 0

    for file_path in temp_dir.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                pass  # Skip files that can't be deleted

    return {'deleted_count': deleted_count, 'cutoff_date': datetime.utcfromtimestamp(cutoff_time).isoformat()}


@register_task('cleanup_old_backups', max_retries=1)
def cleanup_old_backups_task(days_to_keep: int = 30):
    """Clean up backup records and files older than specified days."""
    from app import db
    from app.models import BackupRecord

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    old_backups = db.session.query(BackupRecord).filter(BackupRecord.created_at < cutoff_date).all()

    deleted_count = 0
    for backup in old_backups:
        try:
            if backup.file_path and os.path.exists(backup.file_path):
                os.remove(backup.file_path)
            db.session.delete(backup)
            deleted_count += 1
        except Exception as e:
            pass  # Skip backups that can't be deleted

    db.session.commit()
    return {'deleted_count': deleted_count, 'cutoff_date': cutoff_date.isoformat()}


@register_task('archive_completed_jobs', max_retries=1)
def archive_completed_jobs_task(days_to_archive: int = 30):
    """Archive completed jobs older than specified days."""
    from app import db
    from app.models import BackgroundJob

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_archive)
    # Mark old completed jobs as archived (don't delete, keep for audit trail)
    updated = (
        db.session.query(BackgroundJob)
        .filter(
            (BackgroundJob.status == 'completed')
            & (BackgroundJob.completed_at < cutoff_date)
            & (~BackgroundJob.archived)
        )
        .update({'archived': True})
    )
    db.session.commit()
    return {'archived_count': updated, 'cutoff_date': cutoff_date.isoformat()}


@register_task('database_optimization', max_retries=1)
def database_optimization_task():
    """Run database optimization/vacuum."""
    from app import db

    result = db.session.execute('PRAGMA optimize;')
    db.session.commit()
    return {'status': 'completed', 'message': 'Database optimized'}
