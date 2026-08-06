"""Add original_filename, stored_filename, width, and height to images table

Revision ID: 002_stage1_image_dimensions
Revises: 001_stage0_initial_models
Create Date: 2026-08-06 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_stage1_image_dimensions'
down_revision: Union[str, None] = '001_stage0_initial_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('images', sa.Column('original_filename', sa.String(length=255), nullable=True))
    op.add_column('images', sa.Column('stored_filename', sa.String(length=255), nullable=True))
    op.add_column('images', sa.Column('width', sa.Integer(), nullable=True))
    op.add_column('images', sa.Column('height', sa.Integer(), nullable=True))

    # Backfill original_filename and stored_filename from existing filename column if any
    op.execute("UPDATE images SET original_filename = filename WHERE original_filename IS NULL;")
    op.execute("UPDATE images SET stored_filename = filename WHERE stored_filename IS NULL;")

    op.alter_column('images', 'original_filename', nullable=False)
    op.alter_column('images', 'stored_filename', nullable=False)


def downgrade() -> None:
    op.drop_column('images', 'height')
    op.drop_column('images', 'width')
    op.drop_column('images', 'stored_filename')
    op.drop_column('images', 'original_filename')
