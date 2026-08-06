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
    storage_path = Column(String(512), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)
    status = Column(
        SQLEnum(ImageStatus),
        default=ImageStatus.PENDING,
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, filename='{self.filename}', status='{self.status}')>"
