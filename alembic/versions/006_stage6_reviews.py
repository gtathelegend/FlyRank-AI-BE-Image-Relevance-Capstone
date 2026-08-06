"""Stage 6 review workflow models and status tracking

Revision ID: 006_stage6_reviews
Revises: 005_stage4_suggestions
Create Date: 2026-08-06 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_stage6_reviews'
down_revision: Union[str, None] = '005_stage4_suggestions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum reviewstatus
    reviewstatus_enum = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='reviewstatus')
    reviewstatus_enum.create(op.get_bind(), checkfirst=True)

    # Add review_status column to suggestions
    op.add_column(
        'suggestions',
        sa.Column('review_status', reviewstatus_enum, server_default='PENDING', nullable=False)
    )
    op.create_index(op.f('ix_suggestions_review_status'), 'suggestions', ['review_status'], unique=False)

    # Add FK constraint for review_decisions.suggestion_id -> suggestions.id
    op.create_foreign_key(
        'fk_review_decisions_suggestion_id_suggestions',
        'review_decisions',
        'suggestions',
        ['suggestion_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('fk_review_decisions_suggestion_id_suggestions', 'review_decisions', type_='foreignkey')
    op.drop_index(op.f('ix_suggestions_review_status'), table_name='suggestions')
    op.drop_column('suggestions', 'review_status')
    op.execute("DROP TYPE IF EXISTS reviewstatus;")
