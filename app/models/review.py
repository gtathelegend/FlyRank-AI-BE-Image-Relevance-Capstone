import enum
from sqlalchemy import Column, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class ReviewAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    OVERRIDE = "OVERRIDE"


class ReviewDecision(Base, UUIDMixin, TimestampMixin):
    """Human-in-the-loop review decision tracking model."""
    __tablename__ = "review_decisions"

    suggestion_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    reviewer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    action = Column(
        SQLEnum(ReviewAction),
        nullable=False,
        index=True
    )
    override_image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("images.id", ondelete="SET NULL"),
        nullable=True
    )
    feedback_notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ReviewDecision(id={self.id}, action='{self.action}')>"
