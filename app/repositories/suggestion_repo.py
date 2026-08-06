from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.suggestion import Suggestion
from app.repositories.base import BaseRepository


class SuggestionRepository(BaseRepository[Suggestion]):
    """Data access repository for Suggestion records."""

    def __init__(self):
        super().__init__(Suggestion)

    async def get_by_post_id(self, db: AsyncSession, post_id: UUID) -> List[Suggestion]:
        """Retrieve all suggestions for a specific blog post, ordered by rank."""
        query = select(Suggestion).where(Suggestion.post_id == post_id).order_by(Suggestion.rank.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def delete_by_post_id(self, db: AsyncSession, post_id: UUID) -> None:
        """Clear existing suggestions for a blog post before re-matching."""
        await db.execute(delete(Suggestion).where(Suggestion.post_id == post_id))
        await db.flush()


suggestion_repo = SuggestionRepository()
