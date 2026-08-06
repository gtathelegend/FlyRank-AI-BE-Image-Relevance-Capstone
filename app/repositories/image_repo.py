from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.image import Image, ImageStatus
from app.repositories.base import BaseRepository


class ImageRepository(BaseRepository[Image]):
    """Data access repository for Image records."""

    def __init__(self):
        super().__init__(Image)

    async def get_by_hash(self, db: AsyncSession, file_hash: str) -> Optional[Image]:
        """Find existing image by SHA-256 file hash."""
        result = await db.execute(select(Image).where(Image.file_hash == file_hash))
        return result.scalars().first()

    async def list_images(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ImageStatus] = None
    ) -> List[Image]:
        """Retrieve paginated images with optional status filtering."""
        query = select(Image)
        if status:
            query = query.where(Image.status == status)
        query = query.order_by(Image.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())


image_repo = ImageRepository()
