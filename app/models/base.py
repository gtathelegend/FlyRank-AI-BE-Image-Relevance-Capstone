import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps to models."""
    created_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )


class UUIDMixin:
    """Mixin for adding a primary key UUID to models."""
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
