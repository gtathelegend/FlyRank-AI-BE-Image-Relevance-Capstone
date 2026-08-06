import enum
from sqlalchemy import Column, String, Integer, JSON, Enum as SQLEnum
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class JobType(str, enum.Enum):
    IMAGE_INDEXING = "IMAGE_INDEXING"
    POST_MATCHING = "POST_MATCHING"
    BATCH_EMBEDDING = "BATCH_EMBEDDING"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BatchJob(Base, UUIDMixin, TimestampMixin):
    """Background batch job tracking model."""
    __tablename__ = "batch_jobs"

    job_type = Column(
        SQLEnum(JobType),
        nullable=False,
        index=True
    )
    status = Column(
        SQLEnum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    total_items = Column(Integer, default=0, nullable=False)
    processed_items = Column(Integer, default=0, nullable=False)
    error_details = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<BatchJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"
