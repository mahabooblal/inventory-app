from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class StockIn(db.Model):
    __tablename__ = 'stock_in'
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='ck_stock_in_quantity_positive'),
        db.Index('ix_stock_in_product_created', 'product_id', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), index=True)
    batch_reference = db.Column(db.String(100), index=True)
    expires_on = db.Column(db.Date, index=True)
    receive_date = db.Column(UTCDateTime(), default=utc_now, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    note = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    product = db.relationship('Product', back_populates='stock_entries')
    supplier = db.relationship('Supplier', back_populates='stock_entries')
    user = db.relationship('User')


class StockMovement(db.Model):
    __tablename__ = 'stock_movements'
    __table_args__ = (
        db.CheckConstraint("movement_type in ('incoming', 'outgoing', 'adjustment', 'return', 'transfer')", name='ck_stock_movements_type'),
        db.Index('ix_stock_movements_product_date', 'product_id', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    movement_type = db.Column(db.String(20), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    quantity_before = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    quantity_after = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    batch_reference = db.Column(db.String(100), index=True)
    expires_on = db.Column(db.Date, index=True)
    reference_type = db.Column(db.String(40))
    reference_id = db.Column(db.Integer)
    note = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    product = db.relationship('Product', back_populates='stock_movements')
    user = db.relationship('User')
