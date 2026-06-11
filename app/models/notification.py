from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='info', server_default='info')
    is_read = db.Column(db.Boolean, nullable=False, default=False, server_default='0', index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    user = db.relationship('User', back_populates='notifications')
