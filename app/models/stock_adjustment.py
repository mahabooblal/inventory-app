from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class StockAdjustment(db.Model):
    __tablename__ = 'stock_adjustments'
    __table_args__ = (
        db.CheckConstraint("status in ('pending', 'approved', 'rejected', 'cancelled')", name='ck_stock_adjustments_status'),
        db.CheckConstraint(
            "adjustment_type in ('damage', 'loss', 'correction', 'found', 'expiry')",
            name='ck_stock_adjustments_type',
        ),
        db.CheckConstraint('quantity_delta != 0', name='ck_stock_adjustments_delta_non_zero'),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    adjustment_type = db.Column(db.String(30), nullable=False, index=True)
    quantity_delta = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending', server_default='pending', index=True)
    reason = db.Column(db.String(255), nullable=False)
    rejection_reason = db.Column(db.String(255))
    cancellation_reason = db.Column(db.String(255))
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    approved_at = db.Column(UTCDateTime())
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    product = db.relationship('Product')
    requester = db.relationship('User', foreign_keys=[requested_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
