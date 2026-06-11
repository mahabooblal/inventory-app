from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Sale(db.Model):
    __tablename__ = 'sales'
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='ck_sales_quantity_positive'),
        db.CheckConstraint('selling_price >= 0', name='ck_sales_selling_price_non_negative'),
        db.CheckConstraint('total_amount >= 0', name='ck_sales_total_amount_non_negative'),
        db.Index('ix_sales_product_date', 'product_id', 'sale_date'),
        db.Index('ix_sales_customer_date', 'customer_id', 'sale_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), index=True)
    quantity = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    destination_details = db.Column(db.String(255))
    sale_date = db.Column(UTCDateTime(), default=utc_now, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)

    product = db.relationship('Product', back_populates='sales')
    customer = db.relationship('Customer', back_populates='sales')
    user = db.relationship('User')
