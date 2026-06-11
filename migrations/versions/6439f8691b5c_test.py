"""test

Revision ID: 6439f8691b5c
Revises: e0689a7db83c
Create Date: 2026-05-17 14:28:47.811630

"""
from alembic import op
import sqlalchemy as sa


revision = '6439f8691b5c'
down_revision = 'e0689a7db83c'
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


def _add_column_if_missing(table_name, column):
    if _table_exists(table_name) and not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name, table_name, columns, unique=False):
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(index_name, table_name):
    if _table_exists(table_name) and _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _drop_column_if_exists(table_name, column_name):
    if _table_exists(table_name) and _column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade():
    _add_column_if_missing('products', sa.Column('barcode', sa.String(length=100), nullable=True))
    _create_index_if_missing('ix_products_barcode', 'products', ['barcode'], unique=True)

    _add_column_if_missing('users', sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False))
    _add_column_if_missing('users', sa.Column('api_token', sa.String(length=64), nullable=True))
    _create_index_if_missing('ix_users_api_token', 'users', ['api_token'], unique=True)


def downgrade():
    _drop_index_if_exists('ix_users_api_token', 'users')
    _drop_column_if_exists('users', 'api_token')
    _drop_column_if_exists('users', 'is_active')

    _drop_index_if_exists('ix_products_barcode', 'products')
    _drop_column_if_exists('products', 'barcode')
