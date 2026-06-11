from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Warehouse(db.Model):
    __tablename__ = 'warehouses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    address = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default='1', index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)
    updated_at = db.Column(UTCDateTime(), default=utc_now, onupdate=utc_now, index=True)

    stock_balances = db.relationship('WarehouseStock', back_populates='warehouse', cascade='all, delete-orphan')


class WarehouseStock(db.Model):
    __tablename__ = 'warehouse_stock'
    __table_args__ = (
        db.UniqueConstraint('warehouse_id', 'product_id', name='uq_warehouse_stock_product'),
        db.CheckConstraint('quantity >= 0', name='ck_warehouse_stock_quantity_non_negative'),
    )

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    updated_at = db.Column(UTCDateTime(), default=utc_now, onupdate=utc_now, index=True)

    warehouse = db.relationship('Warehouse', back_populates='stock_balances')
    product = db.relationship('Product')


class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'
    __table_args__ = (
        db.CheckConstraint("status in ('pending', 'completed', 'rejected', 'cancelled')", name='ck_stock_transfers_status'),
        db.CheckConstraint('quantity > 0', name='ck_stock_transfers_quantity_positive'),
    )

    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    source_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False, index=True)
    destination_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending', server_default='pending', index=True)
    note = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    rejection_reason = db.Column(db.String(255))
    cancellation_reason = db.Column(db.String(255))
    approved_at = db.Column(UTCDateTime())
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    product = db.relationship('Product')
    source_warehouse = db.relationship('Warehouse', foreign_keys=[source_warehouse_id])
    destination_warehouse = db.relationship('Warehouse', foreign_keys=[destination_warehouse_id])
    requester = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
