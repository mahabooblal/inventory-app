import os

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.models.audit_log import log_audit_event
from app.services.backup_service import BackupService
from app.utils.permissions import roles_required

bp = Blueprint('backup_admin', __name__, url_prefix='/admin/backup')

PAGE_SIZE = 10


@bp.route('/')
@login_required
@roles_required('admin')
def dashboard():
    page = int(request.args.get('page', 1))
    BackupService.sync_filesystem()
    pagination = BackupService.get_paginated_backups(page=page, per_page=PAGE_SIZE)
    backups = pagination.items
    all_backups = BackupService.get_all_backups()
    failed = [b for b in all_backups if b.status != 'ok']
    storage_used = sum(b.file_size or 0 for b in all_backups)
    last = all_backups[0] if all_backups else None
    reconciliation = BackupService.reconcile_backups()
    return render_template(
        'admin/backup_dashboard.html',
        backups=backups,
        page=page,
        total=pagination.total,
        page_size=PAGE_SIZE,
        last=last,
        failed=failed,
        storage_used=storage_used,
        reconciliation=reconciliation,
        summary={
            'last_backup': last.created_at if last else None,
            'health': 'ok' if last and last.status == 'ok' and not reconciliation['checksum_mismatches'] else 'degraded',
            'total': pagination.total,
            'storage': storage_used,
            'failed': len(failed),
        },
    )


@bp.route('/download/<filename>')
@login_required
@roles_required('admin')
def download_backup(filename):
    record = BackupService.get_backup_by_filename(filename)
    if record is None:
        abort(404)
    file_path = BackupService.safe_backup_path(filename)
    if not os.path.exists(file_path):
        abort(404)
    log_audit_event(current_user, request, 'backup_download', filename, 'initiated')
    return send_from_directory(BackupService.backup_dir(), filename, as_attachment=True)


@bp.route('/delete/<filename>', methods=['POST'])
@login_required
@roles_required('admin')
def delete_backup(filename):
    record = BackupService.get_backup_by_filename(filename)
    if record is None:
        abort(404)
    try:
        BackupService.delete_backup(record.id, delete_file=True)
        flash('Backup deleted.', 'success')
    except Exception as exc:
        log_audit_event(current_user, request, 'backup_delete', filename, f'error: {exc}')
        flash('Delete failed.', 'danger')
    return redirect(url_for('.dashboard'))


@bp.route('/run', methods=['POST'])
@login_required
@roles_required('admin')
def manual_backup():
    ok, result = BackupService.run_backup(backup_type='manual', created_by=current_user)
    if ok:
        flash('Backup completed.', 'success')
    else:
        flash(f'Backup failed: {result}', 'danger')
    return redirect(url_for('.dashboard'))


@bp.route('/verify/<filename>', methods=['POST'])
@login_required
@roles_required('admin')
def verify(filename):
    record = BackupService.get_backup_by_filename(filename)
    if record is None:
        abort(404)
    updated = BackupService.verify_backup(record.id)
    ok = updated and updated.verification_status == 'verified'
    flash('Checksum valid.' if ok else 'Backup verification failed.', 'success' if ok else 'danger')
    return redirect(url_for('.dashboard'))


@bp.route('/restore/<filename>', methods=['POST'])
@login_required
@roles_required('admin')
def restore(filename):
    record = BackupService.get_backup_by_filename(filename)
    if record is None:
        abort(404)
    # Queue restore via task layer (no long-running work in routes)
    dry = request.form.get('dry_run') in ('1', 'true', 'on', 'yes')
    if dry:
        BackupService.queue_restore_dry_run(record.id, current_user)
        flash('Dry-run restore queued; validation will run in background.', 'info')
    else:
        BackupService.queue_restore(record.id, current_user)
        flash('Restore queued; processing will happen in background.', 'info')
    return redirect(url_for('.dashboard'))
