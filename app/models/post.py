import enum
from sqlalchemy import Column, String, Text, JSON, Enum as SQLEnum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class PostStatus(str, enum.Enum):
    PENDING = "PENDING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class BlogPost(Base, UUIDMixin, TimestampMixin):
    """Blog post model representing target content for image matching."""
    __tablename__ = "blog_posts"

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    status = Column(
        SQLEnum(PostStatus),
        default=PostStatus.PENDING,
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<BlogPost(id={self.id}, title='{self.title}', status='{self.status}')>"
