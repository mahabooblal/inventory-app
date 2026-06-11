import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now



class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # Role: 'admin', 'manager', 'staff'
    role = db.Column(db.String(30), nullable=False, default='staff', server_default='staff', index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now)
    # Profile fields
    profile_image = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    preferred_theme = db.Column(db.String(20), nullable=False, default='system', server_default='system')
    dashboard_density = db.Column(db.String(20), nullable=False, default='comfortable', server_default='comfortable')
    email_notifications = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    api_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    # Relationship to activity logs (if activity_log model has user_id)
    activity_logs = db.relationship('ActivityLog', back_populates='user', lazy='dynamic')
    operation_timelines = db.relationship('OperationTimeline', back_populates='user', lazy='dynamic')
    # Notifications
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')

    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role == 'manager'

    def is_staff(self):
        return self.role == 'staff'

    def has_role(self, *roles):
        return self.role in roles

    def get_id(self):
        if not self.is_active:
            return None
        return str(self.id)

    def generate_api_token(self):
        self.api_token = secrets.token_urlsafe(32)
        return self.api_token

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
