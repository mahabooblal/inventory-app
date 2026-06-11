"""Fix warehouse schema drift

Revision ID: 20260601_fix_warehouse_schema
Revises: add_supplier_updated_at
Create Date: 2026-06-01 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20260601_fix_warehouse_schema'
down_revision = 'add_supplier_updated_at'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name, column_name):
    if not _table_exists(table_name):
        return False
    return any(column['name'] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def _constraint_exists(table_name, constraint_name):
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(constraint['name'] == constraint_name for constraint in inspector.get_check_constraints(table_name))


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if _table_exists('warehouses') and not _column_exists('warehouses', 'updated_at'):
        op.add_column('warehouses', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        if dialect == 'postgresql':
            op.execute(sa.text('UPDATE warehouses SET updated_at = COALESCE(created_at, NOW()) WHERE updated_at IS NULL'))
        else:
            op.execute(sa.text('UPDATE warehouses SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL'))

    if _table_exists('stock_transfers'):
        if dialect == 'postgresql':
            if _constraint_exists('stock_transfers', 'ck_stock_transfers_status'):
                op.drop_constraint('ck_stock_transfers_status', 'stock_transfers', type_='check')
            op.create_check_constraint(
                'ck_stock_transfers_status',
                'stock_transfers',
                "status in ('pending', 'completed', 'rejected', 'cancelled')",
            )
            op.alter_column('stock_transfers', 'status', server_default='pending')
        else:
            # SQLite cannot reliably drop check constraints in-place. Existing SQLite
            # development databases can still be repaired with create_all/batch migrations.
            pass


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if _table_exists('stock_transfers') and dialect == 'postgresql':
        if _constraint_exists('stock_transfers', 'ck_stock_transfers_status'):
            op.drop_constraint('ck_stock_transfers_status', 'stock_transfers', type_='check')
        op.create_check_constraint(
            'ck_stock_transfers_status',
            'stock_transfers',
            "status in ('pending', 'completed', 'cancelled')",
        )
        op.alter_column('stock_transfers', 'status', server_default='completed')

    if _table_exists('warehouses') and _column_exists('warehouses', 'updated_at'):
        op.drop_column('warehouses', 'updated_at')
