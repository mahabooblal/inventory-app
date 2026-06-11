from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    __table_args__ = (
        db.CheckConstraint(
            "status in ('draft', 'pending', 'ordered', 'partially_received', 'received', 'cancelled', 'rejected')",
            name='ck_purchase_orders_status',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default='draft', server_default='draft', index=True)
    rejection_reason = db.Column(db.String(255))
    cancellation_reason = db.Column(db.String(255))
    expected_date = db.Column(db.Date)
    notes = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    approved_at = db.Column(UTCDateTime())
    ordered_at = db.Column(UTCDateTime())
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)
    updated_at = db.Column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    supplier = db.relationship('Supplier')
    requester = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    items = db.relationship('PurchaseOrderItem', back_populates='purchase_order', cascade='all, delete-orphan')

    @property
    def total_amount(self):
        return sum(item.line_total for item in self.items)

    @property
    def total_ordered_quantity(self):
        return sum(item.quantity_ordered for item in self.items)

    @property
    def total_received_quantity(self):
        return sum(item.quantity_received for item in self.items)


class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    __table_args__ = (
        db.CheckConstraint('quantity_ordered > 0', name='ck_po_items_quantity_ordered_positive'),
        db.CheckConstraint('quantity_received >= 0', name='ck_po_items_quantity_received_non_negative'),
        db.CheckConstraint('unit_cost >= 0', name='ck_po_items_unit_cost_non_negative'),
    )

    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity_ordered = db.Column(db.Integer, nullable=False)
    quantity_received = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    batch_reference = db.Column(db.String(100), index=True)
    expires_on = db.Column(db.Date, index=True)

    purchase_order = db.relationship('PurchaseOrder', back_populates='items')
    product = db.relationship('Product')

    @property
    def remaining_quantity(self):
        return max(0, self.quantity_ordered - self.quantity_received)

    @property
    def line_total(self):
        return self.quantity_ordered * self.unit_cost
