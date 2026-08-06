from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.analytics_service import analytics_service
from app.schemas.analytics import (
    SystemMetricsResponse,
    CostMetricsResponse,
    JobMetricsResponse
)

router = APIRouter()


@router.get(
    "",
    response_model=SystemMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get system overview metrics",
    description="Retrieve overall system analytics including images processed, API call counts, average latency, total tokens, cost estimates, job statuses, and daily/monthly trends."
)
async def get_system_metrics(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns main system-wide analytics overview.
    """
    logger.info("Executing system metrics API call...")
    return await analytics_service.get_system_metrics(db)


@router.get(
    "/cost",
    response_model=CostMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get cost and token analytics",
    description="Retrieve detailed financial metrics, token consumption counts, cost breakdown by operation type and AI model, and daily/monthly cost trends."
)
async def get_cost_metrics(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns cost and token usage breakdown.
    """
    logger.info("Executing cost metrics API call...")
    return await analytics_service.get_cost_metrics(db)


@router.get(
    "/jobs",
    response_model=JobMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job execution metrics",
    description="Retrieve batch job status distributions, success rates, average duration/latency, and job counts by job type."
)
async def get_job_metrics(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns batch job execution analytics.
    """
    logger.info("Executing job metrics API call...")
    return await analytics_service.get_job_metrics(db)
