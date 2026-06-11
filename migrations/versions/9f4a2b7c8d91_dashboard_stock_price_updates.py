"""Dashboard stock and price update extensions

Revision ID: 9f4a2b7c8d91
Revises: 6439f8691b5c
Create Date: 2026-05-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '9f4a2b7c8d91'
down_revision = '6439f8691b5c'
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


def _create_index(index_name, table_name, columns):
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade():
    _add_column('products', sa.Column('image_filename', sa.String(length=255), nullable=True))
    _add_column('products', sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False))
    _create_index('ix_products_is_active', 'products', ['is_active'])

    _add_column('stock_in', sa.Column('batch_reference', sa.String(length=100), nullable=True))
    _add_column('stock_in', sa.Column('receive_date', sa.DateTime(timezone=True), nullable=True))
    _add_column('stock_in', sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False))
    _create_index('ix_stock_in_batch_reference', 'stock_in', ['batch_reference'])
    _create_index('ix_stock_in_receive_date', 'stock_in', ['receive_date'])

    _add_column('sales', sa.Column('destination_details', sa.String(length=255), nullable=True))

    if not _table_exists('stock_movements'):
        op.create_table(
            'stock_movements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('movement_type', sa.String(length=20), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('reference_type', sa.String(length=40), nullable=True),
            sa.Column('reference_id', sa.Integer(), nullable=True),
            sa.Column('note', sa.String(length=255), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("movement_type in ('incoming', 'outgoing', 'adjustment')", name='ck_stock_movements_type'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    _create_index('ix_stock_movements_created_at', 'stock_movements', ['created_at'])
    _create_index('ix_stock_movements_created_by', 'stock_movements', ['created_by'])
    _create_index('ix_stock_movements_movement_type', 'stock_movements', ['movement_type'])
    _create_index('ix_stock_movements_product_date', 'stock_movements', ['product_id', 'created_at'])
    _create_index('ix_stock_movements_product_id', 'stock_movements', ['product_id'])

    if not _table_exists('price_history'):
        op.create_table(
            'price_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('old_price', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('new_price', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('approval_note', sa.String(length=255), nullable=True),
            sa.Column('margin_percent', sa.Numeric(precision=8, scale=2), server_default='0', nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint('old_price >= 0', name='ck_price_history_old_price_non_negative'),
            sa.CheckConstraint('new_price >= 0', name='ck_price_history_new_price_non_negative'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    _create_index('ix_price_history_created_at', 'price_history', ['created_at'])
    _create_index('ix_price_history_created_by', 'price_history', ['created_by'])
    _create_index('ix_price_history_effective_date', 'price_history', ['effective_date'])
    _create_index('ix_price_history_product_effective', 'price_history', ['product_id', 'effective_date'])
    _create_index('ix_price_history_product_id', 'price_history', ['product_id'])


def downgrade():
    for table_name in ('price_history', 'stock_movements'):
        if _table_exists(table_name):
            op.drop_table(table_name)

    for table_name, column_name in (
        ('sales', 'destination_details'),
        ('stock_in', 'unit_cost'),
        ('stock_in', 'receive_date'),
        ('stock_in', 'batch_reference'),
        ('products', 'is_active'),
        ('products', 'image_filename'),
    ):
        if _column_exists(table_name, column_name):
            op.drop_column(table_name, column_name)
