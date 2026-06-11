"""
Add operation_timeline table for workflow audit/history
"""
from alembic import op
import sqlalchemy as sa

revision = '20260529_add_operation_timeline'
down_revision = 'd4f2a91c8b77'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'operation_timelines',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_type', sa.String(length=50), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('comment', sa.String(length=255)),
        sa.Column('extra', sa.JSON()),
    )
    op.add_column('purchase_orders', sa.Column('rejection_reason', sa.String(length=255), nullable=True))
    op.add_column('purchase_orders', sa.Column('cancellation_reason', sa.String(length=255), nullable=True))
    op.add_column('stock_adjustments', sa.Column('rejection_reason', sa.String(length=255), nullable=True))
    op.add_column('stock_adjustments', sa.Column('cancellation_reason', sa.String(length=255), nullable=True))
    op.add_column('return_orders', sa.Column('rejection_reason', sa.String(length=255), nullable=True))
    op.add_column('return_orders', sa.Column('cancellation_reason', sa.String(length=255), nullable=True))
    op.add_column('stock_transfers', sa.Column('rejection_reason', sa.String(length=255), nullable=True))
    op.add_column('stock_transfers', sa.Column('cancellation_reason', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('stock_transfers', 'cancellation_reason')
    op.drop_column('stock_transfers', 'rejection_reason')
    op.drop_column('return_orders', 'cancellation_reason')
    op.drop_column('return_orders', 'rejection_reason')
    op.drop_column('stock_adjustments', 'cancellation_reason')
    op.drop_column('stock_adjustments', 'rejection_reason')
    op.drop_column('purchase_orders', 'cancellation_reason')
    op.drop_column('purchase_orders', 'rejection_reason')
    op.drop_table('operation_timelines')
