from sqlalchemy import Column, String, Text, Float, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class ImageMetadata(Base, UUIDMixin, TimestampMixin):
    """AI-extracted structured vision metadata for catalog images."""
    __tablename__ = "image_metadata"

    image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("images.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    primary_subject = Column(String(255), nullable=False)
    secondary_subjects = Column(JSON, default=list, nullable=False)
    caption = Column(Text, nullable=False)
    scene_description = Column(Text, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    objects = Column(JSON, default=list, nullable=False)
    animals = Column(JSON, default=list, nullable=False)
    colors = Column(JSON, default=list, nullable=False)
    environment = Column(String(255), nullable=False)
    ocr_text = Column(Text, nullable=True, default="")
    confidence = Column(Float, nullable=False, default=1.0)
    safety_notes = Column(Text, nullable=True, default="")
    model_version = Column(String(100), nullable=False, default="gemini-1.5-flash")

    def __repr__(self) -> str:
        return f"<ImageMetadata(id={self.id}, image_id={self.image_id}, primary_subject='{self.primary_subject}')>"
