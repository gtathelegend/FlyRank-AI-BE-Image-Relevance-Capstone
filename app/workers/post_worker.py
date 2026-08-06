from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.post import BlogPost, PostStatus
from app.models.job import BatchJob, JobStatus, JobType
from app.repositories.post_repo import post_repo
from app.repositories.job_repo import job_repo
from app.services.embedding_pipeline import embedding_pipeline


class PostWorkerService:
    """Background worker executing asynchronous blog post embedding generation."""

    async def process_post_embedding_job(
        self,
        db: AsyncSession,
        job_id: UUID,
        post_id: UUID
    ) -> BatchJob:
        """
        Processes embedding generation for a newly created blog post.
        """
        logger.info(f"Worker started: Post embedding processing for post_id={post_id}, job_id={job_id}")

        job = await job_repo.get(db, job_id)
        post = await post_repo.get(db, post_id)

        if not job or not post:
            logger.error(f"Worker error: Job or Post not found (job_id={job_id}, post_id={post_id})")
            if job:
                job.status = JobStatus.FAILED
                job.error_details = {"error": "Blog post not found"}
                await db.commit()
            raise ValueError("Job or Post not found")

        if post.status == PostStatus.INDEXED or job.status == JobStatus.COMPLETED:
            logger.info(f"Worker skipping: Post embedding already completed for post_id={post_id}")
            return job


        job.status = JobStatus.RUNNING
        await db.commit()

        try:
            # Generate and store post embeddings
            await embedding_pipeline.generate_and_store_post_embedding(
                db=db,
                post_id=post.id,
                title=post.title,
                content=post.content,
                summary=post.summary,
                job_id=job.id
            )

            # Update post and job statuses
            post.status = PostStatus.INDEXED
            job.status = JobStatus.COMPLETED
            job.processed_items = 1
            await db.commit()

            logger.info(f"Post embedding completed & INDEXED for post_id={post.id}")
            return job

        except Exception as e:
            logger.error(f"Post embedding generation failed for post_id={post.id}: {e}")
            post.status = PostStatus.FAILED
            job.status = JobStatus.FAILED
            job.error_details = {"error": str(e)}
            await db.commit()
            raise


post_worker = PostWorkerService()
