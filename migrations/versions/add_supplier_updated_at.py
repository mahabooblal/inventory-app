"""add_supplier_updated_at

Revision ID: add_supplier_updated_at
Revises: add_supplier_is_active
Create Date: 2026-06-01 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_supplier_updated_at'
down_revision = 'add_supplier_is_active'
branch_labels = None
depends_on = None


def upgrade():
    """Add updated_at column to suppliers table"""
    with op.batch_alter_table('suppliers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))


def downgrade():
    """Remove updated_at column from suppliers table"""
    with op.batch_alter_table('suppliers', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
