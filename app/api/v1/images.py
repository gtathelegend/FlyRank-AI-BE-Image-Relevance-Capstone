from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.logging import logger
from app.models.image import Image, ImageStatus
from app.models.job import JobType, JobStatus
from app.repositories.image_repo import image_repo
from app.repositories.job_repo import job_repo
from app.schemas.image import ImageResponse, SingleUploadResponse, BatchUploadResponse
from app.services.storage_service import storage_service

router = APIRouter()


@router.post(
    "/upload",
    response_model=SingleUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Single Image",
    description="Uploads and validates a single image asset, saves to storage, and queues an indexing batch job."
)
@router.post(
    "",
    response_model=SingleUploadResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False
)
async def upload_single_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> SingleUploadResponse:
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided in upload request."
        )

    # 1. Save and validate image
    content, original_filename, stored_filename, file_path, width, height, file_hash = (
        await storage_service.save_image(file)
    )

    # 2. Persist Image DB Record
    image_record = await image_repo.create(
        db,
        {
            "filename": original_filename,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "storage_path": str(file_path),
            "content_type": file.content_type or "image/jpeg",
            "file_size": len(content),
            "width": width,
            "height": height,
            "file_hash": file_hash,
            "status": ImageStatus.PENDING
        }
    )

    # 3. Create Queued BatchJob
    job = await job_repo.create_job(
        db,
        job_type=JobType.IMAGE_INDEXING,
        total_items=1,
        status=JobStatus.PENDING
    )

    logger.info(f"BatchJob created: id={job.id} for image_id={image_record.id}")

    return SingleUploadResponse(
        message="Image uploaded successfully and background job queued.",
        image=ImageResponse.model_validate(image_record),
        job_id=job.id
    )


@router.post(
    "/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Multiple Images in Batch",
    description="Uploads and processes multiple image files in batch, saving valid files and queuing a batch job."
)
async def upload_batch_images(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
) -> BatchUploadResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided in batch upload request."
        )

    uploaded_images: List[ImageResponse] = []
    errors: List[str] = []

    # Create BatchJob first
    job = await job_repo.create_job(
        db,
        job_type=JobType.IMAGE_INDEXING,
        total_items=len(files),
        status=JobStatus.PENDING
    )
    logger.info(f"BatchJob created for batch upload: id={job.id}, total_files={len(files)}")

    for file in files:
        original_filename = file.filename or "unknown.jpg"
        try:
            content, orig_name, stored_name, file_path, width, height, file_hash = (
                await storage_service.save_image(file)
            )

            image_record = await image_repo.create(
                db,
                {
                    "filename": orig_name,
                    "original_filename": orig_name,
                    "stored_filename": stored_name,
                    "storage_path": str(file_path),
                    "content_type": file.content_type or "image/jpeg",
                    "file_size": len(content),
                    "width": width,
                    "height": height,
                    "file_hash": file_hash,
                    "status": ImageStatus.PENDING
                }
            )
            uploaded_images.append(ImageResponse.model_validate(image_record))
        except HTTPException as he:
            error_msg = f"Validation failure for '{original_filename}': {he.detail}"
            logger.warning(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Storage failure for '{original_filename}': {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return BatchUploadResponse(
        message=f"Batch upload complete. {len(uploaded_images)}/{len(files)} uploaded successfully.",
        total_uploaded=len(uploaded_images),
        job_id=job.id,
        images=uploaded_images,
        errors=errors
    )


@router.get(
    "",
    response_model=List[ImageResponse],
    status_code=status.HTTP_200_OK,
    summary="List Images",
    description="Retrieves a paginated list of catalog images with optional status filtering."
)
async def list_images(
    skip: int = Query(0, ge=0, description="Offset pagination skip"),
    limit: int = Query(100, ge=1, le=500, description="Page limit"),
    image_status: Optional[ImageStatus] = Query(None, description="Filter by image status"),
    db: AsyncSession = Depends(get_db)
) -> List[ImageResponse]:
    images = await image_repo.list_images(db, skip=skip, limit=limit, status=image_status)
    return [ImageResponse.model_validate(img) for img in images]


@router.get(
    "/{id}",
    response_model=ImageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Image Metadata",
    description="Retrieves details and storage metadata for a specific image by UUID."
)
async def get_image(
    id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ImageResponse:
    image = await image_repo.get(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID '{id}' not found."
        )
    return ImageResponse.model_validate(image)


@router.get(
    "/{id}/metadata",
    status_code=status.HTTP_200_OK,
    summary="Get AI Image Vision Metadata",
    description="Retrieves AI-generated structured vision metadata for a processed image asset."
)
async def get_image_vision_metadata(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.metadata_repo import metadata_repo

    image = await image_repo.get(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID '{id}' not found."
        )

    metadata = await metadata_repo.get_by_image_id(db, id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Vision metadata not yet processed or available for image '{id}'."
        )

    return {
        "id": str(metadata.id),
        "image_id": str(metadata.image_id),
        "primary_subject": metadata.primary_subject,
        "secondary_subjects": metadata.secondary_subjects,
        "caption": metadata.caption,
        "scene_description": metadata.scene_description,
        "tags": metadata.tags,
        "objects": metadata.objects,
        "animals": metadata.animals,
        "colors": metadata.colors,
        "environment": metadata.environment,
        "ocr_text": metadata.ocr_text,
        "confidence": metadata.confidence,
        "safety_notes": metadata.safety_notes,
        "model_version": metadata.model_version,
        "created_at": metadata.created_at
    }


@router.get(
    "/{id}/embedding",
    status_code=status.HTTP_200_OK,
    summary="Get Image Vector Embedding Metadata",
    description="Retrieves vector embedding metadata for a processed image asset."
)
async def get_image_embedding_metadata(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.embedding_repo import image_embedding_repo

    image = await image_repo.get(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID '{id}' not found."
        )

    embedding = await image_embedding_repo.get_by_image_id(db, id)
    if not embedding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vector embedding not yet generated for image '{id}'."
        )

    return {
        "id": str(embedding.id),
        "image_id": str(embedding.image_id),
        "dimension": embedding.dimension,
        "model_name": embedding.model_name,
        "status": embedding.status,
        "created_at": embedding.created_at
    }


