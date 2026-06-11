"""Initial schema

Revision ID: e0689a7db83c
Revises:
Create Date: 2026-05-17 11:48:05.598954

"""
from alembic import op
import sqlalchemy as sa


revision = 'e0689a7db83c'
down_revision = None
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


def _create_index_if_missing(index_name, table_name, columns, unique=False):
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _add_column_if_missing(table_name, column):
    if _table_exists(table_name) and not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    if not _table_exists('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('username', sa.String(length=80), nullable=False),
            sa.Column('email', sa.String(length=120), nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=30), server_default='staff', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('profile_image', sa.String(length=255), nullable=True),
            sa.Column('bio', sa.Text(), nullable=True),
            sa.Column('phone', sa.String(length=30), nullable=True),
            sa.Column('preferred_theme', sa.String(length=20), server_default='system', nullable=False),
            sa.Column('dashboard_density', sa.String(length=20), server_default='comfortable', nullable=False),
            sa.Column('email_notifications', sa.Boolean(), server_default='1', nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
            sa.UniqueConstraint('username'),
        )

    if not _table_exists('categories'):
        op.create_table(
            'categories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
        )

    if not _table_exists('suppliers'):
        op.create_table(
            'suppliers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('email', sa.String(length=120), nullable=True),
            sa.Column('phone', sa.String(length=30), nullable=True),
            sa.Column('address', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _table_exists('customers'):
        op.create_table(
            'customers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('email', sa.String(length=120), nullable=True),
            sa.Column('phone', sa.String(length=30), nullable=True),
            sa.Column('address', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
        )

    if not _table_exists('products'):
        op.create_table(
            'products',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('sku', sa.String(length=80), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('price', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('cost_price', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('quantity', sa.Integer(), server_default='0', nullable=False),
            sa.Column('low_stock_limit', sa.Integer(), server_default='10', nullable=False),
            sa.Column('category_id', sa.Integer(), nullable=True),
            sa.Column('supplier_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint('cost_price >= 0', name='ck_products_cost_price_non_negative'),
            sa.CheckConstraint('low_stock_limit >= 0', name='ck_products_low_stock_limit_non_negative'),
            sa.CheckConstraint('price >= 0', name='ck_products_price_non_negative'),
            sa.CheckConstraint('quantity >= 0', name='ck_products_quantity_non_negative'),
            sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
            sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('sku'),
        )

    if not _table_exists('stock_in'):
        op.create_table(
            'stock_in',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('supplier_id', sa.Integer(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('note', sa.String(length=255), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint('quantity > 0', name='ck_stock_in_quantity_positive'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _table_exists('sales'):
        op.create_table(
            'sales',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('selling_price', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('sale_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.CheckConstraint('quantity > 0', name='ck_sales_quantity_positive'),
            sa.CheckConstraint('selling_price >= 0', name='ck_sales_selling_price_non_negative'),
            sa.CheckConstraint('total_amount >= 0', name='ck_sales_total_amount_non_negative'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
            sa.ForeignKeyConstraint(['product_id'], ['products.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _table_exists('reports'):
        op.create_table(
            'reports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('report_type', sa.String(length=80), nullable=False),
            sa.Column('from_date', sa.Date(), nullable=True),
            sa.Column('to_date', sa.Date(), nullable=True),
            sa.Column('file_path', sa.String(length=255), nullable=True),
            sa.Column('generated_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['generated_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _table_exists('activity_logs'):
        op.create_table(
            'activity_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('action', sa.String(length=40), nullable=False),
            sa.Column('entity_type', sa.String(length=80), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('old_values', sa.Text(), nullable=True),
            sa.Column('new_values', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _table_exists('notifications'):
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('message', sa.String(length=255), nullable=False),
            sa.Column('type', sa.String(length=20), server_default='info', nullable=False),
            sa.Column('is_read', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    _create_index_if_missing('ix_activity_logs_action_created', 'activity_logs', ['action', 'created_at'])
    _create_index_if_missing('ix_activity_logs_created_at', 'activity_logs', ['created_at'])
    _create_index_if_missing('ix_activity_logs_entity', 'activity_logs', ['entity_type', 'entity_id'])
    _create_index_if_missing('ix_activity_logs_user_id', 'activity_logs', ['user_id'])
    _create_index_if_missing('ix_notifications_user_id', 'notifications', ['user_id'])
    _create_index_if_missing('ix_products_category_id', 'products', ['category_id'])
    _create_index_if_missing('ix_products_name', 'products', ['name'])
    _create_index_if_missing('ix_products_supplier_id', 'products', ['supplier_id'])
    _create_index_if_missing('ix_sales_created_by', 'sales', ['created_by'])
    _create_index_if_missing('ix_sales_customer_date', 'sales', ['customer_id', 'sale_date'])
    _create_index_if_missing('ix_sales_customer_id', 'sales', ['customer_id'])
    _create_index_if_missing('ix_sales_product_date', 'sales', ['product_id', 'sale_date'])
    _create_index_if_missing('ix_sales_product_id', 'sales', ['product_id'])
    _create_index_if_missing('ix_sales_sale_date', 'sales', ['sale_date'])
    _create_index_if_missing('ix_stock_in_created_at', 'stock_in', ['created_at'])
    _create_index_if_missing('ix_stock_in_created_by', 'stock_in', ['created_by'])
    _create_index_if_missing('ix_stock_in_product_created', 'stock_in', ['product_id', 'created_at'])
    _create_index_if_missing('ix_stock_in_product_id', 'stock_in', ['product_id'])
    _create_index_if_missing('ix_stock_in_supplier_id', 'stock_in', ['supplier_id'])
    _create_index_if_missing('ix_users_role', 'users', ['role'])


def downgrade():
    for table_name in (
        'notifications',
        'activity_logs',
        'reports',
        'sales',
        'stock_in',
        'products',
        'customers',
        'suppliers',
        'categories',
        'users',
    ):
        if _table_exists(table_name):
            op.drop_table(table_name)
