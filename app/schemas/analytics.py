from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DailyUsageSchema(BaseModel):
    """Daily breakdown of AI token usage, costs, and operation volume."""
    date: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    operations_count: int

    model_config = ConfigDict(from_attributes=True)


class MonthlyUsageSchema(BaseModel):
    """Monthly breakdown of AI token usage, costs, and operation volume."""
    month: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    operations_count: int

    model_config = ConfigDict(from_attributes=True)


class SystemMetricsResponse(BaseModel):
    """Overall system dashboard metrics summary."""
    images_processed: int
    vision_api_calls: int
    embedding_api_calls: int
    mismatch_guard_api_calls: int
    average_latency_seconds: float
    estimated_token_usage: int
    estimated_cost_usd: float
    successful_jobs: int
    failed_jobs: int
    average_processing_time_seconds: float
    average_similarity_score: float
    daily_usage: List[DailyUsageSchema]
    monthly_usage: List[MonthlyUsageSchema]

    model_config = ConfigDict(from_attributes=True)


class CostMetricsResponse(BaseModel):
    """Detailed financial and token consumption metrics."""
    estimated_cost_usd: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_by_operation: Dict[str, float]
    cost_by_model: Dict[str, float]
    daily_usage: List[DailyUsageSchema]
    monthly_usage: List[MonthlyUsageSchema]

    model_config = ConfigDict(from_attributes=True)


class JobMetricsResponse(BaseModel):
    """Background batch job execution performance metrics."""
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    pending_jobs: int
    running_jobs: int
    success_rate: float
    average_latency_seconds: float
    average_processing_time_seconds: float
    jobs_by_type: Dict[str, int]

    model_config = ConfigDict(from_attributes=True)
