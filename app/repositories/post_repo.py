from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.post import BlogPost, PostStatus
from app.repositories.base import BaseRepository


class BlogPostRepository(BaseRepository[BlogPost]):
    """Data access repository for BlogPost records."""

    def __init__(self):
        super().__init__(BlogPost)

    async def list_posts(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[PostStatus] = None
    ) -> List[BlogPost]:
        """Retrieve paginated blog posts with optional status filter."""
        query = select(BlogPost)
        if status:
            query = query.where(BlogPost.status == status)
        query = query.order_by(BlogPost.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())


post_repo = BlogPostRepository()
