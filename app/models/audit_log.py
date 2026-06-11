from app import db
from app.models.types import UTCDateTime
from flask import request as flask_request
from datetime import datetime, timezone

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    username = db.Column(db.String(80), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    target = db.Column(db.String(255), nullable=True)
    result = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(UTCDateTime(), default=datetime.utcnow, index=True)


def log_audit_event(user, req, action, target, result):
    from app import db
    # Prefer explicit req, then Flask request context, otherwise label as 'system'
    ip = None
    if req is not None:
        ip = getattr(req, 'remote_addr', None)
    if not ip:
        try:
            ip = getattr(flask_request, 'remote_addr', None)
        except Exception:
            ip = None
    if not ip:
        ip = 'system'

    user_id = None
    username = None
    if isinstance(user, dict):
        user_id = user.get('id') or user.get('user_id')
        username = user.get('username')
    else:
        user_id = getattr(user, 'id', None)
        username = getattr(user, 'username', None)

    log = AuditLog(
        user_id=user_id,
        username=username,
        ip_address=ip,
        action=action,
        target=target,
        result=result,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(log)
    db.session.commit()
