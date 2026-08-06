from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import BatchJob, JobType, JobStatus
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[BatchJob]):
    """Data access repository for BatchJob records."""

    def __init__(self):
        super().__init__(BatchJob)

    async def create_job(
        self,
        db: AsyncSession,
        job_type: JobType,
        total_items: int = 1,
        status: JobStatus = JobStatus.PENDING
    ) -> BatchJob:
        """Create a new batch job tracking record."""
        return await self.create(
            db,
            {
                "job_type": job_type,
                "status": status,
                "total_items": total_items,
                "processed_items": 0,
                "error_details": None
            }
        )


job_repo = JobRepository()
