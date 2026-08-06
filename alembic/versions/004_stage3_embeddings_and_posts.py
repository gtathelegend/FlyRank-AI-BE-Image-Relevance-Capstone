"""Create blog_posts, image_embeddings, and post_embeddings tables

Revision ID: 004_stage3_embeddings_and_posts
Revises: 003_stage2_image_metadata
Create Date: 2026-08-06 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_stage3_embeddings_and_posts'
down_revision: Union[str, None] = '003_stage2_image_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create blog_posts table
    op.create_table(
        'blog_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'INDEXED', 'FAILED', name='poststatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_blog_posts_status'), 'blog_posts', ['status'], unique=False)

    # 2. Create image_embeddings table
    op.create_table(
        'image_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('dimension', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('image_id')
    )
    op.create_index(op.f('ix_image_embeddings_image_id'), 'image_embeddings', ['image_id'], unique=True)

    # 3. Create post_embeddings table
    op.create_table(
        'post_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title_vector', sa.JSON(), nullable=False),
        sa.Column('content_vector', sa.JSON(), nullable=False),
        sa.Column('combined_vector', sa.JSON(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('dimension', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id')
    )
    op.create_index(op.f('ix_post_embeddings_post_id'), 'post_embeddings', ['post_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_post_embeddings_post_id'), table_name='post_embeddings')
    op.drop_table('post_embeddings')
    op.drop_index(op.f('ix_image_embeddings_image_id'), table_name='image_embeddings')
    op.drop_table('image_embeddings')
    op.drop_index(op.f('ix_blog_posts_status'), table_name='blog_posts')
    op.drop_table('blog_posts')
    op.execute("DROP TYPE IF EXISTS poststatus;")
