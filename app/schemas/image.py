from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.image import ImageStatus


class ImageResponse(BaseModel):
    """Schema for individual image details."""
    id: UUID
    filename: str
    original_filename: str
    stored_filename: str
    content_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    file_hash: Optional[str] = None
    status: ImageStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SingleUploadResponse(BaseModel):
    """Schema for single image upload response."""
    message: str = "Image uploaded successfully"
    image: ImageResponse
    job_id: UUID


class BatchUploadResponse(BaseModel):
    """Schema for batch image upload response."""
    message: str
    total_uploaded: int
    job_id: UUID
    images: List[ImageResponse]
    errors: List[str] = []
