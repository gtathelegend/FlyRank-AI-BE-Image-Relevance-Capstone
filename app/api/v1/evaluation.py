from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.evaluation_engine import evaluation_engine
from app.schemas.evaluation import EvaluationReportResponse, MetricSummarySchema

router = APIRouter()


@router.get(
    "",
    response_model=EvaluationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Run evaluation report",
    description="Calculates comprehensive evaluation metrics, confusion matrix summary, and extracts top failure cases."
)
async def get_evaluation_report(
    db: AsyncSession = Depends(get_db)
):
    """
    Executes evaluation suite over ground-truth dataset and system match suggestions.
    Returns complete evaluation report.
    """
    logger.info("Executing evaluation report API call...")
    return await evaluation_engine.run_evaluation(db)


@router.get(
    "/metrics",
    response_model=MetricSummarySchema,
    status_code=status.HTTP_200_OK,
    summary="Get evaluation metrics",
    description="Returns quantitative evaluation metrics including Precision@1, Precision@3, Precision@5, acceptance/rejection rates, and average confidence."
)
async def get_evaluation_metrics(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns quantitative evaluation metrics summary.
    """
    logger.info("Fetching evaluation metrics API call...")
    report = await evaluation_engine.run_evaluation(db)
    return report.metrics
