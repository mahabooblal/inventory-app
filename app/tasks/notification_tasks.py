"""Notification background tasks."""

from app.tasks.runner import register_task


@register_task('send_email_notification', max_retries=3)
def send_email_notification_task(recipient: str, subject: str, body: str, html: str = None):
    """Send email notification in background."""
    from app.services.notification_service import NotificationService

    service = NotificationService()
    result = service.send_email(recipient=recipient, subject=subject, body=body, html=html)
    return {'notification_id': result.id, 'status': result.status}


@register_task('notify_approval_request', max_retries=2)
def notify_approval_request_task(approval_id: int, approver_id: int):
    """Notify approver of pending approval request."""
    from app.services.notification_service import NotificationService
    from app.models import User

    approver = User.query.get(approver_id)
    if not approver:
        raise ValueError(f'Approver {approver_id} not found')

    service = NotificationService()
    result = service.notify_approval_request(approval_id=approval_id, approver=approver)
    return {'notification_id': result.id, 'approver_id': approver_id}


@register_task('notify_low_stock', max_retries=2)
def notify_low_stock_task(product_id: int):
    """Notify relevant users of low stock."""
    from app.services.notification_service import NotificationService

    service = NotificationService()
    count = service.notify_low_stock(product_id=product_id)
    return {'product_id': product_id, 'notified_count': count}


@register_task('notify_backup_completion', max_retries=2)
def notify_backup_completion_task(backup_id: int, status: str, error_message: str = None):
    """Notify admins of backup completion status."""
    from app.services.notification_service import NotificationService

    service = NotificationService()
    count = service.notify_backup_completion(
        backup_id=backup_id, status=status, error_message=error_message
    )
    return {'backup_id': backup_id, 'notified_count': count}
