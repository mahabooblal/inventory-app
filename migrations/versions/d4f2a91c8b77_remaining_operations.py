"""Remaining operations modules

Revision ID: d4f2a91c8b77
Revises: c1f8e6a4b2d0
Create Date: 2026-05-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f2a91c8b77'
down_revision = 'c1f8e6a4b2d0'
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
    if not _table_exists('warehouses'):
        op.create_table(
            'warehouses',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('code', sa.String(length=30), nullable=False),
            sa.Column('address', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code'),
            sa.UniqueConstraint('name'),
        )
    _create_index('ix_warehouses_code', 'warehouses', ['code'], unique=True)
    _create_index('ix_warehouses_created_at', 'warehouses', ['created_at'])
    _create_index('ix_warehouses_is_active', 'warehouses', ['is_active'])
    _create_index('ix_warehouses_name', 'warehouses', ['name'], unique=True)

    if not _table_exists('warehouse_stock'):
        op.create_table(
            'warehouse_stock',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('warehouse_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), server_default='0', nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint('quantity >= 0', name='ck_warehouse_stock_quantity_non_negative'),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('warehouse_id', 'product_id', name='uq_warehouse_stock_product'),
        )
    _create_index('ix_warehouse_stock_product_id', 'warehouse_stock', ['product_id'])
    _create_index('ix_warehouse_stock_updated_at', 'warehouse_stock', ['updated_at'])
    _create_index('ix_warehouse_stock_warehouse_id', 'warehouse_stock', ['warehouse_id'])

    if not _table_exists('stock_transfers'):
        op.create_table(
            'stock_transfers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('transfer_number', sa.String(length=40), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('source_warehouse_id', sa.Integer(), nullable=False),
            sa.Column('destination_warehouse_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='completed', nullable=False),
            sa.Column('note', sa.String(length=255), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("status in ('pending', 'completed', 'cancelled')", name='ck_stock_transfers_status'),
            sa.CheckConstraint('quantity > 0', name='ck_stock_transfers_quantity_positive'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['destination_warehouse_id'], ['warehouses.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.ForeignKeyConstraint(['source_warehouse_id'], ['warehouses.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('transfer_number'),
        )
    _create_index('ix_stock_transfers_created_at', 'stock_transfers', ['created_at'])
    _create_index('ix_stock_transfers_created_by', 'stock_transfers', ['created_by'])
    _create_index('ix_stock_transfers_destination_warehouse_id', 'stock_transfers', ['destination_warehouse_id'])
    _create_index('ix_stock_transfers_product_id', 'stock_transfers', ['product_id'])
    _create_index('ix_stock_transfers_source_warehouse_id', 'stock_transfers', ['source_warehouse_id'])
    _create_index('ix_stock_transfers_status', 'stock_transfers', ['status'])
    _create_index('ix_stock_transfers_transfer_number', 'stock_transfers', ['transfer_number'], unique=True)

    if not _table_exists('return_orders'):
        op.create_table(
            'return_orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('return_number', sa.String(length=40), nullable=False),
            sa.Column('return_type', sa.String(length=20), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=True),
            sa.Column('supplier_id', sa.Integer(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('refund_amount', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('restock', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('reason', sa.String(length=255), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='processed', nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("return_type in ('customer', 'supplier')", name='ck_return_orders_type'),
            sa.CheckConstraint("status in ('processed', 'refunded', 'closed')", name='ck_return_orders_status'),
            sa.CheckConstraint('quantity > 0', name='ck_return_orders_quantity_positive'),
            sa.CheckConstraint('refund_amount >= 0', name='ck_return_orders_refund_non_negative'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('return_number'),
        )
    _create_index('ix_return_orders_created_at', 'return_orders', ['created_at'])
    _create_index('ix_return_orders_created_by', 'return_orders', ['created_by'])
    _create_index('ix_return_orders_customer_id', 'return_orders', ['customer_id'])
    _create_index('ix_return_orders_product_id', 'return_orders', ['product_id'])
    _create_index('ix_return_orders_return_number', 'return_orders', ['return_number'], unique=True)
    _create_index('ix_return_orders_return_type', 'return_orders', ['return_type'])
    _create_index('ix_return_orders_status', 'return_orders', ['status'])
    _create_index('ix_return_orders_supplier_id', 'return_orders', ['supplier_id'])


def downgrade():
    for table_name in ('return_orders', 'stock_transfers', 'warehouse_stock', 'warehouses'):
        if _table_exists(table_name):
            op.drop_table(table_name)
