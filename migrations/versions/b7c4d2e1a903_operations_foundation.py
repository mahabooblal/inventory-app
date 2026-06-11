"""Operations foundation for purchase orders and stock audit

Revision ID: b7c4d2e1a903
Revises: 9f4a2b7c8d91
Create Date: 2026-05-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c4d2e1a903'
down_revision = '9f4a2b7c8d91'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name, column_name):
    if not _table_exists(table_name):
        return False
    return any(column['name'] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def _index_exists(table_name, index_name):
    if not _table_exists(table_name):
        return False
    return any(index['name'] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def _add_column(table_name, column):
    if _table_exists(table_name) and not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _create_index(index_name, table_name, columns, unique=False):
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade():
    _add_column('activity_logs', sa.Column('old_values', sa.Text(), nullable=True))
    _add_column('activity_logs', sa.Column('new_values', sa.Text(), nullable=True))
    _add_column('activity_logs', sa.Column('ip_address', sa.String(length=45), nullable=True))
    _add_column('activity_logs', sa.Column('user_agent', sa.String(length=255), nullable=True))

    _add_column('stock_in', sa.Column('expires_on', sa.Date(), nullable=True))
    _create_index('ix_stock_in_expires_on', 'stock_in', ['expires_on'])

    _add_column('stock_movements', sa.Column('quantity_before', sa.Integer(), server_default='0', nullable=False))
    _add_column('stock_movements', sa.Column('quantity_after', sa.Integer(), server_default='0', nullable=False))
    _add_column('stock_movements', sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False))
    _add_column('stock_movements', sa.Column('batch_reference', sa.String(length=100), nullable=True))
    _add_column('stock_movements', sa.Column('expires_on', sa.Date(), nullable=True))
    _create_index('ix_stock_movements_batch_reference', 'stock_movements', ['batch_reference'])
    _create_index('ix_stock_movements_expires_on', 'stock_movements', ['expires_on'])

    if not _table_exists('purchase_orders'):
        op.create_table(
            'purchase_orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('po_number', sa.String(length=40), nullable=False),
            sa.Column('supplier_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=30), server_default='draft', nullable=False),
            sa.Column('expected_date', sa.Date(), nullable=True),
            sa.Column('notes', sa.String(length=255), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('ordered_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("status in ('draft', 'ordered', 'partially_received', 'received', 'cancelled')", name='ck_purchase_orders_status'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('po_number'),
        )
    _create_index('ix_purchase_orders_created_at', 'purchase_orders', ['created_at'])
    _create_index('ix_purchase_orders_created_by', 'purchase_orders', ['created_by'])
    _create_index('ix_purchase_orders_po_number', 'purchase_orders', ['po_number'], unique=True)
    _create_index('ix_purchase_orders_status', 'purchase_orders', ['status'])
    _create_index('ix_purchase_orders_supplier_id', 'purchase_orders', ['supplier_id'])

    if not _table_exists('purchase_order_items'):
        op.create_table(
            'purchase_order_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('purchase_order_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('quantity_ordered', sa.Integer(), nullable=False),
            sa.Column('quantity_received', sa.Integer(), server_default='0', nullable=False),
            sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('batch_reference', sa.String(length=100), nullable=True),
            sa.Column('expires_on', sa.Date(), nullable=True),
            sa.CheckConstraint('quantity_ordered > 0', name='ck_po_items_quantity_ordered_positive'),
            sa.CheckConstraint('quantity_received >= 0', name='ck_po_items_quantity_received_non_negative'),
            sa.CheckConstraint('unit_cost >= 0', name='ck_po_items_unit_cost_non_negative'),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    _create_index('ix_purchase_order_items_batch_reference', 'purchase_order_items', ['batch_reference'])
    _create_index('ix_purchase_order_items_expires_on', 'purchase_order_items', ['expires_on'])
    _create_index('ix_purchase_order_items_product_id', 'purchase_order_items', ['product_id'])
    _create_index('ix_purchase_order_items_purchase_order_id', 'purchase_order_items', ['purchase_order_id'])

    if not _table_exists('stock_adjustments'):
        op.create_table(
            'stock_adjustments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('adjustment_type', sa.String(length=30), nullable=False),
            sa.Column('quantity_delta', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
            sa.Column('reason', sa.String(length=255), nullable=False),
            sa.Column('requested_by', sa.Integer(), nullable=False),
            sa.Column('approved_by', sa.Integer(), nullable=True),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("status in ('pending', 'approved', 'rejected')", name='ck_stock_adjustments_status'),
            sa.CheckConstraint("adjustment_type in ('damage', 'loss', 'correction', 'found', 'expiry')", name='ck_stock_adjustments_type'),
            sa.CheckConstraint('quantity_delta != 0', name='ck_stock_adjustments_delta_non_zero'),
            sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.ForeignKeyConstraint(['requested_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    _create_index('ix_stock_adjustments_adjustment_type', 'stock_adjustments', ['adjustment_type'])
    _create_index('ix_stock_adjustments_approved_by', 'stock_adjustments', ['approved_by'])
    _create_index('ix_stock_adjustments_created_at', 'stock_adjustments', ['created_at'])
    _create_index('ix_stock_adjustments_product_id', 'stock_adjustments', ['product_id'])
    _create_index('ix_stock_adjustments_requested_by', 'stock_adjustments', ['requested_by'])
    _create_index('ix_stock_adjustments_status', 'stock_adjustments', ['status'])


def downgrade():
    for table_name in ('stock_adjustments', 'purchase_order_items', 'purchase_orders'):
        if _table_exists(table_name):
            op.drop_table(table_name)
