"""Invoice billing and payments

Revision ID: c1f8e6a4b2d0
Revises: b7c4d2e1a903
Create Date: 2026-05-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c1f8e6a4b2d0'
down_revision = 'b7c4d2e1a903'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name, index_name):
    if not _table_exists(table_name):
        return False
    return any(index['name'] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def _create_index(index_name, table_name, columns, unique=False):
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade():
    if not _table_exists('invoices'):
        op.create_table(
            'invoices',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('invoice_number', sa.String(length=40), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=30), server_default='issued', nullable=False),
            sa.Column('subtotal', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('total_amount', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('amount_paid', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('notes', sa.String(length=255), nullable=True),
            sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("status in ('draft', 'issued', 'paid', 'partially_paid', 'cancelled')", name='ck_invoices_status'),
            sa.CheckConstraint('subtotal >= 0', name='ck_invoices_subtotal_non_negative'),
            sa.CheckConstraint('discount_amount >= 0', name='ck_invoices_discount_non_negative'),
            sa.CheckConstraint('tax_amount >= 0', name='ck_invoices_tax_non_negative'),
            sa.CheckConstraint('total_amount >= 0', name='ck_invoices_total_non_negative'),
            sa.CheckConstraint('amount_paid >= 0', name='ck_invoices_paid_non_negative'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('invoice_number'),
        )
    _create_index('ix_invoices_created_at', 'invoices', ['created_at'])
    _create_index('ix_invoices_created_by', 'invoices', ['created_by'])
    _create_index('ix_invoices_customer_id', 'invoices', ['customer_id'])
    _create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'], unique=True)
    _create_index('ix_invoices_issued_at', 'invoices', ['issued_at'])
    _create_index('ix_invoices_status', 'invoices', ['status'])

    if not _table_exists('invoice_items'):
        op.create_table(
            'invoice_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('invoice_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
            sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.CheckConstraint('quantity > 0', name='ck_invoice_items_quantity_positive'),
            sa.CheckConstraint('unit_price >= 0', name='ck_invoice_items_unit_price_non_negative'),
            sa.CheckConstraint('discount_amount >= 0', name='ck_invoice_items_discount_non_negative'),
            sa.CheckConstraint('tax_rate >= 0', name='ck_invoice_items_tax_rate_non_negative'),
            sa.CheckConstraint('line_total >= 0', name='ck_invoice_items_line_total_non_negative'),
            sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    _create_index('ix_invoice_items_invoice_id', 'invoice_items', ['invoice_id'])
    _create_index('ix_invoice_items_product_id', 'invoice_items', ['product_id'])

    if not _table_exists('payments'):
        op.create_table(
            'payments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('invoice_id', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('method', sa.String(length=30), server_default='cash', nullable=False),
            sa.Column('reference', sa.String(length=100), nullable=True),
            sa.Column('received_by', sa.Integer(), nullable=True),
            sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint('amount > 0', name='ck_payments_amount_positive'),
            sa.CheckConstraint("method in ('cash', 'card', 'upi', 'bank_transfer', 'credit', 'other')", name='ck_payments_method'),
            sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
            sa.ForeignKeyConstraint(['received_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    _create_index('ix_payments_invoice_id', 'payments', ['invoice_id'])
    _create_index('ix_payments_method', 'payments', ['method'])
    _create_index('ix_payments_received_at', 'payments', ['received_at'])
    _create_index('ix_payments_received_by', 'payments', ['received_by'])


def downgrade():
    for table_name in ('payments', 'invoice_items', 'invoices'):
        if _table_exists(table_name):
            op.drop_table(table_name)
