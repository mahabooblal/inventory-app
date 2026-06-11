from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now

class OperationTimeline(db.Model):
    __tablename__ = 'operation_timelines'
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # e.g. 'PurchaseOrder', 'StockTransfer', etc.
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)  # e.g. 'created', 'submitted', 'approved', 'rejected', 'cancelled', 'reversed', 'commented'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    timestamp = db.Column(UTCDateTime(), default=utc_now, index=True)
    comment = db.Column(db.String(255))  # Optional: reason, note, or comment
    extra = db.Column(db.JSON)  # For storing additional structured data (status, old/new values, etc.)

    user = db.relationship('User', back_populates='operation_timelines')

    def __repr__(self):
        return f'<OperationTimeline {self.entity_type} {self.entity_id} {self.action}>'
