import enum
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class OperationType(str, enum.Enum):
    VISION_ANALYSIS = "VISION_ANALYSIS"
    EMBEDDING_GEN = "EMBEDDING_GEN"
    MISMATCH_GUARD_VERIFICATION = "MISMATCH_GUARD_VERIFICATION"


class CostLog(Base, UUIDMixin, TimestampMixin):
    """Cost logging model tracking AI token consumption and estimated USD cost."""
    __tablename__ = "cost_logs"

    operation_type = Column(
        SQLEnum(OperationType),
        nullable=False,
        index=True
    )
    model_name = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), default=0.0, nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("batch_jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    def __repr__(self) -> str:
        return (
            f"<CostLog(id={self.id}, operation='{self.operation_type}', "
            f"model='{self.model_name}', cost_usd={self.estimated_cost_usd})>"
        )
