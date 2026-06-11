from app import db
from app.models import Notification, User


def create_notification(user_id, message, notification_type='info'):
    notification = Notification(user_id=user_id, message=message, type=notification_type)
    db.session.add(notification)
    db.session.flush()
    return notification


def notify_role_users(roles, message, notification_type='info'):
    users = User.query.filter(User.role.in_(roles)).all()
    for user in users:
        create_notification(user.id, message, notification_type)
    return users


def get_unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_all_notifications_read(user_id):
    updated_count = Notification.query.filter_by(user_id=user_id, is_read=False).update(
        {'is_read': True},
        synchronize_session=False,
    )
    db.session.commit()
    return updated_count


def mark_notification_read(notification_id, user_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first_or_404()
    notification.is_read = True
    db.session.commit()
    return notification
