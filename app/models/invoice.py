from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Invoice(db.Model):
    __tablename__ = 'invoices'
    __table_args__ = (
        db.CheckConstraint("status in ('draft', 'issued', 'paid', 'partially_paid', 'cancelled')", name='ck_invoices_status'),
        db.CheckConstraint('subtotal >= 0', name='ck_invoices_subtotal_non_negative'),
        db.CheckConstraint('discount_amount >= 0', name='ck_invoices_discount_non_negative'),
        db.CheckConstraint('tax_amount >= 0', name='ck_invoices_tax_non_negative'),
        db.CheckConstraint('total_amount >= 0', name='ck_invoices_total_non_negative'),
        db.CheckConstraint('amount_paid >= 0', name='ck_invoices_paid_non_negative'),
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), index=True)
    status = db.Column(db.String(30), nullable=False, default='issued', server_default='issued', index=True)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    notes = db.Column(db.String(255))
    issued_at = db.Column(UTCDateTime(), default=utc_now, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    customer = db.relationship('Customer')
    user = db.relationship('User')
    items = db.relationship('InvoiceItem', back_populates='invoice', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='invoice', cascade='all, delete-orphan')

    @property
    def balance_due(self):
        return max(0, self.total_amount - self.amount_paid)


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='ck_invoice_items_quantity_positive'),
        db.CheckConstraint('unit_price >= 0', name='ck_invoice_items_unit_price_non_negative'),
        db.CheckConstraint('discount_amount >= 0', name='ck_invoice_items_discount_non_negative'),
        db.CheckConstraint('tax_rate >= 0', name='ck_invoice_items_tax_rate_non_negative'),
        db.CheckConstraint('line_total >= 0', name='ck_invoice_items_line_total_non_negative'),
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0, server_default='0')
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    line_total = db.Column(db.Numeric(10, 2), nullable=False)

    invoice = db.relationship('Invoice', back_populates='items')
    product = db.relationship('Product')


class Payment(db.Model):
    __tablename__ = 'payments'
    __table_args__ = (
        db.CheckConstraint('amount > 0', name='ck_payments_amount_positive'),
        db.CheckConstraint("method in ('cash', 'card', 'upi', 'bank_transfer', 'credit', 'other')", name='ck_payments_method'),
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(30), nullable=False, default='cash', server_default='cash', index=True)
    reference = db.Column(db.String(100))
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    received_at = db.Column(UTCDateTime(), default=utc_now, index=True)

    invoice = db.relationship('Invoice', back_populates='payments')
    user = db.relationship('User')
