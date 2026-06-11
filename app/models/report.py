from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(80), nullable=False)
    from_date = db.Column(db.Date)
    to_date = db.Column(db.Date)
    file_path = db.Column(db.String(255))
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(UTCDateTime(), default=utc_now)

    user = db.relationship('User')
