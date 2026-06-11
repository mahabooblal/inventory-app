from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models import ActivityLog, User
from app.utils.permissions import roles_required

bp = Blueprint('activity_logs', __name__, url_prefix='/activity-logs')


@bp.route('/')
@login_required
@roles_required('admin', 'manager')
def list_logs():
    action = request.args.get('action', '').strip()
    entity_type = request.args.get('entity_type', '').strip()
    user_id = request.args.get('user_id', 0, type=int)
    query = ActivityLog.query
    if action:
        query = query.filter(ActivityLog.action == action)
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    logs = query.order_by(ActivityLog.created_at.desc()).limit(250).all()
    users = User.query.order_by(User.username).all()
    entity_types = [row[0] for row in ActivityLog.query.with_entities(ActivityLog.entity_type).distinct().order_by(ActivityLog.entity_type).all()]
    actions = [row[0] for row in ActivityLog.query.with_entities(ActivityLog.action).distinct().order_by(ActivityLog.action).all()]
    return render_template('activity_logs/list.html', title='Activity Logs', logs=logs, users=users, entity_types=entity_types, actions=actions, selected_action=action, selected_entity_type=entity_type, selected_user_id=user_id)
