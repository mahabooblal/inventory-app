from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Product(db.Model):
    __tablename__ = 'products'
    __table_args__ = (
        db.CheckConstraint('price >= 0', name='ck_products_price_non_negative'),
        db.CheckConstraint('cost_price >= 0', name='ck_products_cost_price_non_negative'),
        db.CheckConstraint('quantity >= 0', name='ck_products_quantity_non_negative'),
        db.CheckConstraint('low_stock_limit >= 0', name='ck_products_low_stock_limit_non_negative'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(100), unique=True, nullable=True, index=True)
    image_filename = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default='1', index=True)
    description = db.Column(db.String(255))
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    quantity = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    low_stock_limit = db.Column(db.Integer, nullable=False, default=10, server_default='10')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now)
    updated_at = db.Column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    category = db.relationship('Category', back_populates='products')
    supplier = db.relationship('Supplier', back_populates='products')
    stock_entries = db.relationship('StockIn', back_populates='product', cascade='all, delete-orphan')
    sales = db.relationship('Sale', back_populates='product', cascade='all, delete-orphan')
    price_history = db.relationship('PriceHistory', back_populates='product', cascade='all, delete-orphan')
    stock_movements = db.relationship('StockMovement', back_populates='product', cascade='all, delete-orphan')

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_limit
