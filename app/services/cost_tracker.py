import time
from typing import Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cost import CostLog, OperationType
from app.repositories.base import BaseRepository
from app.core.logging import logger

# Pricing rates per 1,000 tokens
MODEL_PRICING = {
    "gemini-1.5-flash": {
        "input_per_1k": Decimal("0.000075"),
        "output_per_1k": Decimal("0.000300")
    },
    "gemini-2.0-flash": {
        "input_per_1k": Decimal("0.000075"),
        "output_per_1k": Decimal("0.000300")
    },
    "text-embedding-004": {
        "input_per_1k": Decimal("0.000025"),
        "output_per_1k": Decimal("0.000000")
    }
}


class CostTrackerService:
    """Service to record AI operation token usage and estimated USD cost."""

    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> Decimal:
        """Calculates estimated cost in USD based on model rates."""
        rates = MODEL_PRICING.get(model_name, MODEL_PRICING["gemini-1.5-flash"])
        input_cost = (Decimal(input_tokens) / Decimal(1000)) * rates["input_per_1k"]
        output_cost = (Decimal(output_tokens) / Decimal(1000)) * rates["output_per_1k"]
        return round(input_cost + output_cost, 6)

    async def log_cost(
        self,
        db: AsyncSession,
        operation_type: OperationType,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        job_id: Optional[UUID] = None
    ) -> CostLog:
        """Persists a CostLog record into the database."""
        estimated_cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        cost_repo = BaseRepository(CostLog)
        
        cost_entry = await cost_repo.create(
            db,
            {
                "operation_type": operation_type,
                "model_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": estimated_cost,
                "job_id": job_id
            }
        )
        logger.info(
            f"Cost logged: op={operation_type.value}, model={model_name}, "
            f"tokens=in({input_tokens})/out({output_tokens}), cost=${estimated_cost:.6f}"
        )
        return cost_entry


cost_tracker = CostTrackerService()
