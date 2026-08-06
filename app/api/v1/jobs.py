from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.repositories.job_repo import job_repo
from app.models.job import JobStatus
from app.workers.vision_worker import vision_worker

router = APIRouter()


async def _run_worker_job(job_id: UUID):
    from app.api.deps import get_db
    async for db in get_db():
        try:
            await vision_worker.process_batch_job(db, job_id)
        except Exception as e:
            from app.core.logging import logger
            logger.error(f"Background worker failed for job {job_id}: {e}")
        break


@router.post(
    "/{job_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Asynchronous Vision Processing",
    description="Dispatches background worker task to process queued images in a BatchJob."
)
async def process_batch_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    job = await job_repo.get(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BatchJob with ID '{job_id}' not found."
        )

    if job.status == JobStatus.RUNNING:
        return {"message": "Job is already running", "job_id": str(job_id), "status": job.status}

    # Dispatch to background task execution with a fresh session runner
    background_tasks.add_task(_run_worker_job, job_id)

    return {
        "message": "Vision processing worker dispatched successfully.",
        "job_id": str(job_id),
        "status": "QUEUED"
    }



@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Job Status and Details",
    description="Retrieves the current execution status, progress metrics, and error logs for a BatchJob."
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    job = await job_repo.get(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BatchJob with ID '{job_id}' not found."
        )

    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
        "error_details": job.error_details,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }
