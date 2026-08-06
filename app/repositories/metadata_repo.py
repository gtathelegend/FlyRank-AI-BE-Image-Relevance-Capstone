from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.metadata import ImageMetadata
from app.repositories.base import BaseRepository


class ImageMetadataRepository(BaseRepository[ImageMetadata]):
    """Data access repository for ImageMetadata records."""

    def __init__(self):
        super().__init__(ImageMetadata)

    async def get_by_image_id(self, db: AsyncSession, image_id: UUID) -> Optional[ImageMetadata]:
        """Find metadata by associated image_id."""
        result = await db.execute(select(ImageMetadata).where(ImageMetadata.image_id == image_id))
        return result.scalars().first()


metadata_repo = ImageMetadataRepository()
