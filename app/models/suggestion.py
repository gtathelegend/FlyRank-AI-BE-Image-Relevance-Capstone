import enum
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class MatchStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    REJECTED_BY_GUARD = "REJECTED_BY_GUARD"
    NO_CONFIDENT_MATCH = "NO_CONFIDENT_MATCH"


class Suggestion(Base, UUIDMixin, TimestampMixin):
    """Semantic match suggestion model connecting blog posts to top candidate images."""
    __tablename__ = "suggestions"

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("images.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    raw_similarity_score = Column(Float, nullable=False)
    guard_confidence_score = Column(Float, nullable=True, default=1.0)
    final_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    match_status = Column(
        SQLEnum(MatchStatus),
        default=MatchStatus.MATCHED,
        nullable=False,
        index=True
    )
    match_reasoning = Column(Text, nullable=False)
    is_reviewed = Column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Suggestion(id={self.id}, post_id={self.post_id}, image_id={self.image_id}, "
            f"rank={self.rank}, score={self.final_score:.4f})>"
        )
