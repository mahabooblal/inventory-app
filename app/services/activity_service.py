from app import db
from app.models import ActivityLog, OperationTimeline


def log_activity(user_id, action, entity_type, entity_id=None, description=None):
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.session.add(entry)
    return entry


def log_operation_timeline(user_id, entity_type, entity_id, action, comment=None, extra=None):
    entry = OperationTimeline(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        comment=comment,
        extra=extra,
    )
    db.session.add(entry)
    return entry
