from pathlib import Path
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.image import Image, ImageStatus
from app.models.job import BatchJob, JobStatus, JobType
from app.models.metadata import ImageMetadata
from app.repositories.image_repo import image_repo
from app.repositories.job_repo import job_repo
from app.repositories.metadata_repo import metadata_repo
from app.services.vision_pipeline import vision_pipeline


class VisionWorkerService:
    """Background worker executing asynchronous AI Vision processing jobs."""

    async def process_batch_job(self, db: AsyncSession, job_id: UUID) -> BatchJob:
        """
        Executes vision processing for all pending images associated with a BatchJob.
        """
        logger.info(f"Worker started: Processing BatchJob id={job_id}")

        job = await job_repo.get(db, job_id)
        if not job:
            logger.error(f"Worker error: BatchJob id={job_id} not found.")
            raise ValueError(f"BatchJob id={job_id} not found.")

        # Update job status to RUNNING
        job.status = JobStatus.RUNNING
        await db.commit()
        await db.refresh(job)

        # Retrieve pending images
        pending_images = await image_repo.list_images(db, limit=job.total_items or 100, status=ImageStatus.PENDING)
        logger.info(f"Worker task loaded {len(pending_images)} pending image(s) for job_id={job.id}")

        error_logs: List[str] = []
        processed_count = 0

        for img in pending_images:
            image_path = Path(img.storage_path)
            logger.info(f"Image processing started for image_id={img.id}, file='{img.original_filename}'")

            try:
                # 1. Mark image status as PROCESSING
                img.status = ImageStatus.PROCESSING
                await db.commit()

                # 2. Verify file exists
                if not image_path.exists():
                    raise FileNotFoundError(f"Image file not found at path: {image_path}")

                # 3. Call AI Vision Pipeline
                vision_result, cost_usd = await vision_pipeline.process_image_vision(
                    db=db,
                    image_path=image_path,
                    job_id=job.id
                )

                # 4. Check if metadata record already exists for this image
                existing_meta = await metadata_repo.get_by_image_id(db, img.id)
                meta_dict = {
                    "image_id": img.id,
                    "primary_subject": vision_result.primary_subject,
                    "secondary_subjects": vision_result.secondary_subjects,
                    "caption": vision_result.caption,
                    "scene_description": vision_result.scene_description,
                    "tags": vision_result.tags,
                    "objects": vision_result.objects,
                    "animals": vision_result.animals,
                    "colors": vision_result.colors,
                    "environment": vision_result.environment,
                    "ocr_text": vision_result.ocr_text or "",
                    "confidence": vision_result.confidence,
                    "safety_notes": vision_result.safety_notes or "",
                    "model_version": vision_pipeline.model_name
                }

                if existing_meta:
                    for key, val in meta_dict.items():
                        setattr(existing_meta, key, val)
                else:
                    await metadata_repo.create(db, meta_dict)

                # 5. Generate and Store Image Vector Embedding
                tags_str = ", ".join(vision_result.tags) if vision_result.tags else ""
                objects_str = ", ".join(vision_result.objects) if vision_result.objects else ""
                metadata_prompt = (
                    f"Subject: {vision_result.primary_subject}. "
                    f"Caption: {vision_result.caption}. "
                    f"Description: {vision_result.scene_description}. "
                    f"Tags: {tags_str}. "
                    f"Objects: {objects_str}. "
                    f"Environment: {vision_result.environment}."
                )

                from app.services.embedding_pipeline import embedding_pipeline
                await embedding_pipeline.generate_and_store_image_embedding(
                    db=db,
                    image_id=img.id,
                    metadata_text=metadata_prompt,
                    job_id=job.id
                )

                # 6. Mark image as PROCESSED
                img.status = ImageStatus.PROCESSED
                processed_count += 1
                job.processed_items = processed_count
                await db.commit()

                logger.info(f"Metadata & Vector Embedding stored for image_id={img.id}")


            except Exception as e:
                logger.error(f"Processing failed for image_id={img.id}: {e}")
                img.status = ImageStatus.FAILED
                error_logs.append(f"Image {img.id} ({img.original_filename}): {str(e)}")
                await db.commit()

        # Final Job Status Update
        if error_logs and processed_count == 0:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.COMPLETED

        if error_logs:
            job.error_details = {"errors": error_logs}

        await db.commit()
        await db.refresh(job)

        logger.info(
            f"Worker batch job completed: id={job.id}, status={job.status}, "
            f"processed={processed_count}/{len(pending_images)}"
        )
        return job


vision_worker = VisionWorkerService()
