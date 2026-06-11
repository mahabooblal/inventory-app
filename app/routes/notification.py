from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.services.notification_service import get_unread_count, mark_all_notifications_read, mark_notification_read
from app.models import Notification

notification_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notification_bp.route('/recent')
@login_required
def recent():
    rows = current_user.notifications.order_by(Notification.created_at.desc()).limit(10).all()
    return jsonify({
        'count': get_unread_count(current_user.id),
        'notifications': [
            {
                'id': item.id,
                'message': item.message,
                'type': item.type,
                'is_read': item.is_read,
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            for item in rows
        ],
    })


@notification_bp.route('/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    updated_count = mark_all_notifications_read(current_user.id)
    return jsonify({'ok': True, 'updated': updated_count, 'count': get_unread_count(current_user.id)})


@notification_bp.route('/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    mark_notification_read(notification_id, current_user.id)
    return jsonify({'ok': True, 'count': get_unread_count(current_user.id)})
