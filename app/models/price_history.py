from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    __table_args__ = (
        db.CheckConstraint('old_price >= 0', name='ck_price_history_old_price_non_negative'),
        db.CheckConstraint('new_price >= 0', name='ck_price_history_new_price_non_negative'),
        db.Index('ix_price_history_product_effective', 'product_id', 'effective_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    old_price = db.Column(db.Numeric(10, 2), nullable=False)
    new_price = db.Column(db.Numeric(10, 2), nullable=False)
    effective_date = db.Column(UTCDateTime(), nullable=False, default=utc_now, index=True)
    approval_note = db.Column(db.String(255))
    margin_percent = db.Column(db.Numeric(8, 2), nullable=False, default=0, server_default='0')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    product = db.relationship('Product', back_populates='price_history')
    user = db.relationship('User')
