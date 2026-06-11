from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class ReturnOrder(db.Model):
    __tablename__ = 'return_orders'
    __table_args__ = (
        db.CheckConstraint("return_type in ('customer', 'supplier')", name='ck_return_orders_type'),
        db.CheckConstraint("status in ('pending', 'approved', 'rejected', 'cancelled', 'processed', 'refunded', 'closed')", name='ck_return_orders_status'),
        db.CheckConstraint('quantity > 0', name='ck_return_orders_quantity_positive'),
        db.CheckConstraint('refund_amount >= 0', name='ck_return_orders_refund_non_negative'),
    )

    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    return_type = db.Column(db.String(20), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), index=True)
    quantity = db.Column(db.Integer, nullable=False)
    refund_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    restock = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending', server_default='pending', index=True)
    rejection_reason = db.Column(db.String(255))
    cancellation_reason = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    approved_at = db.Column(UTCDateTime())
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    product = db.relationship('Product')
    customer = db.relationship('Customer')
    supplier = db.relationship('Supplier')
    requester = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
