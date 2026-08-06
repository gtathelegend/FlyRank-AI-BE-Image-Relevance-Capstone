from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.embedding import ImageEmbedding, PostEmbedding
from app.repositories.base import BaseRepository


class ImageEmbeddingRepository(BaseRepository[ImageEmbedding]):
    """Data access repository for ImageEmbedding records."""

    def __init__(self):
        super().__init__(ImageEmbedding)

    async def get_by_image_id(self, db: AsyncSession, image_id: UUID) -> Optional[ImageEmbedding]:
        """Find embedding vector by associated image_id."""
        result = await db.execute(select(ImageEmbedding).where(ImageEmbedding.image_id == image_id))
        return result.scalars().first()


class PostEmbeddingRepository(BaseRepository[PostEmbedding]):
    """Data access repository for PostEmbedding records."""

    def __init__(self):
        super().__init__(PostEmbedding)

    async def get_by_post_id(self, db: AsyncSession, post_id: UUID) -> Optional[PostEmbedding]:
        """Find embedding vectors by associated post_id."""
        result = await db.execute(select(PostEmbedding).where(PostEmbedding.post_id == post_id))
        return result.scalars().first()


image_embedding_repo = ImageEmbeddingRepository()
post_embedding_repo = PostEmbeddingRepository()
