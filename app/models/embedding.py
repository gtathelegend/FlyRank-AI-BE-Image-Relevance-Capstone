from sqlalchemy import Column, String, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class ImageEmbedding(Base, UUIDMixin, TimestampMixin):
    """Vector embedding model stored for processed catalog images."""
    __tablename__ = "image_embeddings"

    image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("images.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    embedding = Column(JSON, nullable=False)  # 768-dimensional float vector
    model_name = Column(String(100), default="text-embedding-004", nullable=False)
    dimension = Column(Integer, default=768, nullable=False)
    status = Column(String(50), default="COMPLETED", nullable=False)

    def __repr__(self) -> str:
        return f"<ImageEmbedding(id={self.id}, image_id={self.image_id}, dim={self.dimension})>"


class PostEmbedding(Base, UUIDMixin, TimestampMixin):
    """Vector embedding model stored for blog posts."""
    __tablename__ = "post_embeddings"

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    title_vector = Column(JSON, nullable=False)     # 768-dim vector for title
    content_vector = Column(JSON, nullable=False)   # 768-dim vector for main content
    combined_vector = Column(JSON, nullable=False)  # 768-dim weighted vector (title + summary + content)
    model_name = Column(String(100), default="text-embedding-004", nullable=False)
    dimension = Column(Integer, default=768, nullable=False)

    def __repr__(self) -> str:
        return f"<PostEmbedding(id={self.id}, post_id={self.post_id}, dim={self.dimension})>"
