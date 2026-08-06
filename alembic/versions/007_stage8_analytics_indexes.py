"""Stage 8 analytics performance indexes

Revision ID: 007_stage8_analytics_indexes
Revises: 006_stage6_reviews
Create Date: 2026-08-06 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_stage8_analytics_indexes'
down_revision: Union[str, None] = '006_stage6_reviews'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create indexes on created_at columns for analytics queries
    op.create_index(op.f('ix_cost_logs_created_at'), 'cost_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_batch_jobs_created_at'), 'batch_jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_suggestions_created_at'), 'suggestions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_suggestions_created_at'), table_name='suggestions')
    op.drop_index(op.f('ix_batch_jobs_created_at'), table_name='batch_jobs')
    op.drop_index(op.f('ix_cost_logs_created_at'), table_name='cost_logs')
