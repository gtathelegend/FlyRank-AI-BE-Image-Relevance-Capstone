"""Stage 0 initial database models

Revision ID: 001_stage0_initial_models
Revises: 
Create Date: 2026-08-06 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_stage0_initial_models'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create images table
    op.create_table(
        'images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', name='imagestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_images_file_hash'), 'images', ['file_hash'], unique=False)
    op.create_index(op.f('ix_images_status'), 'images', ['status'], unique=False)

    # Create batch_jobs table
    op.create_table(
        'batch_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_type', sa.Enum('IMAGE_INDEXING', 'POST_MATCHING', 'BATCH_EMBEDDING', name='jobtype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='jobstatus'), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=False),
        sa.Column('processed_items', sa.Integer(), nullable=False),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_batch_jobs_job_type'), 'batch_jobs', ['job_type'], unique=False)
    op.create_index(op.f('ix_batch_jobs_status'), 'batch_jobs', ['status'], unique=False)

    # Create cost_logs table
    op.create_table(
        'cost_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation_type', sa.Enum('VISION_ANALYSIS', 'EMBEDDING_GEN', 'MISMATCH_GUARD_VERIFICATION', name='operationtype'), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('estimated_cost_usd', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['batch_jobs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cost_logs_job_id'), 'cost_logs', ['job_id'], unique=False)
    op.create_index(op.f('ix_cost_logs_operation_type'), 'cost_logs', ['operation_type'], unique=False)

    # Create review_decisions table
    op.create_table(
        'review_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.Enum('APPROVE', 'REJECT', 'OVERRIDE', name='reviewaction'), nullable=False),
        sa.Column('override_image_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('feedback_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['override_image_id'], ['images.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_decisions_action'), 'review_decisions', ['action'], unique=False)
    op.create_index(op.f('ix_review_decisions_reviewer_id'), 'review_decisions', ['reviewer_id'], unique=False)
    op.create_index(op.f('ix_review_decisions_suggestion_id'), 'review_decisions', ['suggestion_id'], unique=False)


def downgrade() -> None:
    op.drop_table('review_decisions')
    op.drop_table('cost_logs')
    op.drop_table('batch_jobs')
    op.drop_table('images')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS reviewaction;")
    op.execute("DROP TYPE IF EXISTS operationtype;")
    op.execute("DROP TYPE IF EXISTS jobstatus;")
    op.execute("DROP TYPE IF EXISTS jobtype;")
    op.execute("DROP TYPE IF EXISTS imagestatus;")
