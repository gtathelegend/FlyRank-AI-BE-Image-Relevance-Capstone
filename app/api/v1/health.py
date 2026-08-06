from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import logger
from app.schemas.health import HealthCheckResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check Endpoint",
    description="Verifies operational status of FastAPI service and PostgreSQL database connection."
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthCheckResponse:
    db_status = "connected"
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
    except Exception as e:
        logger.error(f"Health check DB ping failed: {e}")
        db_status = f"error: {str(e)}"

    return HealthCheckResponse(
        status="ok" if db_status == "connected" else "degraded",
        app_name=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        database=db_status
    )
