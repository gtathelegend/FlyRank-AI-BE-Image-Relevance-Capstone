import enum
from sqlalchemy import Column, String, Integer, BigInteger, Enum as SQLEnum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class ImageStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Image(Base, UUIDMixin, TimestampMixin):
    """Image catalog model storing uploaded image asset references."""
    __tablename__ = "images"

    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)
    status = Column(
        SQLEnum(ImageStatus),
        default=ImageStatus.PENDING,
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, original_filename='{self.original_filename}', status='{self.status}')>"

