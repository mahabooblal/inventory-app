"""create backup_records table

Revision ID: backup_records_001
Revises: 
Create Date: 2026-05-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'backup_records_001'
down_revision = '20260529_add_operation_timeline'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'backup_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('backup_type', sa.String(length=32), nullable=False),
        sa.Column('database_type', sa.String(length=16), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('retention_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_status', sa.String(length=32), nullable=True, index=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('restored_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('restore_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restore_status', sa.String(length=32), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_backup_records_created_at', 'backup_records', ['created_at'])
    op.create_index('ix_backup_records_status', 'backup_records', ['status'])
    op.create_index('ix_backup_records_verification_status', 'backup_records', ['verification_status'])

def downgrade():
    op.drop_table('backup_records')
