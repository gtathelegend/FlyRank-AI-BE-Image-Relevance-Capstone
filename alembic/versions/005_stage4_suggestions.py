"""Create suggestions table

Revision ID: 005_stage4_suggestions
Revises: 004_stage3_embeddings_and_posts
Create Date: 2026-08-06 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_stage4_suggestions'
down_revision: Union[str, None] = '004_stage3_embeddings_and_posts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('raw_similarity_score', sa.Float(), nullable=False),
        sa.Column('guard_confidence_score', sa.Float(), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('match_status', sa.Enum('MATCHED', 'REJECTED_BY_GUARD', 'NO_CONFIDENT_MATCH', name='matchstatus'), nullable=False),
        sa.Column('match_reasoning', sa.Text(), nullable=False),
        sa.Column('is_reviewed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suggestions_image_id'), 'suggestions', ['image_id'], unique=False)
    op.create_index(op.f('ix_suggestions_match_status'), 'suggestions', ['match_status'], unique=False)
    op.create_index(op.f('ix_suggestions_post_id'), 'suggestions', ['post_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_suggestions_post_id'), table_name='suggestions')
    op.drop_index(op.f('ix_suggestions_match_status'), table_name='suggestions')
    op.drop_index(op.f('ix_suggestions_image_id'), table_name='suggestions')
    op.drop_table('suggestions')
    op.execute("DROP TYPE IF EXISTS matchstatus;")
