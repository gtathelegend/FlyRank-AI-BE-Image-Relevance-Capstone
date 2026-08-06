"""Create image_metadata table

Revision ID: 003_stage2_image_metadata
Revises: 002_stage1_image_dimensions
Create Date: 2026-08-06 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_stage2_image_metadata'
down_revision: Union[str, None] = '002_stage1_image_dimensions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'image_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('primary_subject', sa.String(length=255), nullable=False),
        sa.Column('secondary_subjects', sa.JSON(), nullable=False),
        sa.Column('caption', sa.Text(), nullable=False),
        sa.Column('scene_description', sa.Text(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('objects', sa.JSON(), nullable=False),
        sa.Column('animals', sa.JSON(), nullable=False),
        sa.Column('colors', sa.JSON(), nullable=False),
        sa.Column('environment', sa.String(length=255), nullable=False),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('safety_notes', sa.Text(), nullable=True),
        sa.Column('model_version', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('image_id')
    )
    op.create_index(op.f('ix_image_metadata_image_id'), 'image_metadata', ['image_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_image_metadata_image_id'), table_name='image_metadata')
    op.drop_table('image_metadata')
