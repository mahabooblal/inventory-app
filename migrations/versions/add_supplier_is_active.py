"""Add is_active to suppliers table

Revision ID: add_supplier_is_active
Revises: backup_records_001
Create Date: 2026-06-01 15:08:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_supplier_is_active'
down_revision = 'backup_records_001'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'suppliers' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('suppliers')]
        if 'is_active' not in columns:
            op.add_column('suppliers', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1', index=True))


def downgrade():
    op.drop_column('suppliers', 'is_active')
