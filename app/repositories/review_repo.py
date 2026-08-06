from typing import List, Optional, Tuple
from datetime import datetime, date, time
from uuid import UUID
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suggestion import Suggestion, ReviewStatus
from app.models.review import ReviewDecision, ReviewAction
from app.repositories.base import BaseRepository
from app.repositories.post_repo import post_repo
from app.repositories.image_repo import image_repo
from app.repositories.metadata_repo import metadata_repo
from app.schemas.review import (
    ReviewResponse,
    ReviewListResponse,
    ReviewDecisionResponse,
    ImageReviewSchema,
    BlogPostReviewSchema,
    MismatchGuardResultSchema
)


class ReviewRepository(BaseRepository[ReviewDecision]):
    """Data access repository for human-in-the-loop review operations."""

    def __init__(self):
        super().__init__(ReviewDecision)

    async def get_suggestion(self, db: AsyncSession, suggestion_id: UUID) -> Optional[Suggestion]:
        """Fetch a match suggestion by its UUID."""
        query = select(Suggestion).where(Suggestion.id == suggestion_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_decisions_for_suggestion(self, db: AsyncSession, suggestion_id: UUID) -> List[ReviewDecision]:
        """Retrieve decision audit trail for a suggestion ordered by newest first."""
        query = (
            select(ReviewDecision)
            .where(ReviewDecision.suggestion_id == suggestion_id)
            .order_by(desc(ReviewDecision.created_at))
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_reviews(
        self,
        db: AsyncSession,
        status: Optional[ReviewStatus] = None,
        image_id: Optional[UUID] = None,
        post_id: Optional[UUID] = None,
        review_date: Optional[date] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Suggestion], int]:
        """
        Queries suggestions supporting status, image, post, and date range filters.
        Returns a tuple of (suggestions_list, total_count).
        """
        query = select(Suggestion)
        count_query = select(func.count()).select_from(Suggestion)

        filters = []

        if status is not None:
            filters.append(Suggestion.review_status == status)

        if image_id is not None:
            filters.append(Suggestion.image_id == image_id)

        if post_id is not None:
            filters.append(Suggestion.post_id == post_id)

        if review_date is not None:
            start_dt = datetime.combine(review_date, time.min)
            end_dt = datetime.combine(review_date, time.max)
            filters.append(Suggestion.created_at >= start_dt)
            filters.append(Suggestion.created_at <= end_dt)
        else:
            if start_date is not None:
                filters.append(Suggestion.created_at >= start_date)
            if end_date is not None:
                filters.append(Suggestion.created_at <= end_date)

        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        # Count total
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        # Execute paginated query ordered by created_at desc
        query = query.order_by(desc(Suggestion.created_at), Suggestion.rank.asc()).offset(skip).limit(limit)
        result = await db.execute(query)
        suggestions = list(result.scalars().all())

        return suggestions, total

    async def record_decision(
        self,
        db: AsyncSession,
        suggestion: Suggestion,
        action: ReviewAction,
        reviewer_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> Tuple[Suggestion, ReviewDecision]:
        """
        Persists a review decision (APPROVE/REJECT), updates suggestion status and is_reviewed flag.
        """
        # Create ReviewDecision record
        decision = ReviewDecision(
            suggestion_id=suggestion.id,
            reviewer_id=reviewer_id,
            action=action,
            feedback_notes=notes
        )
        db.add(decision)

        # Update Suggestion state
        suggestion.is_reviewed = True
        if action == ReviewAction.APPROVE:
            suggestion.review_status = ReviewStatus.APPROVED
        elif action == ReviewAction.REJECT:
            suggestion.review_status = ReviewStatus.REJECTED

        await db.commit()
        await db.refresh(suggestion)
        await db.refresh(decision)

        return suggestion, decision

    async def build_review_response(self, db: AsyncSession, suggestion: Suggestion) -> ReviewResponse:
        """
        Constructs a complete ReviewResponse object combining Suggestion, Image, BlogPost,
        ImageMetadata, and decision history.
        """
        # Fetch blog post
        post = await post_repo.get(db, suggestion.post_id)
        post_schema = None
        if post:
            post_schema = BlogPostReviewSchema(
                id=post.id,
                title=post.title,
                content=post.content,
                author=post.author,
                category=post.category,
                summary=post.summary,
                tags=post.tags or [],
                status=post.status
            )

        # Fetch image
        img = await image_repo.get(db, suggestion.image_id)
        img_schema = None
        if img:
            img_schema = ImageReviewSchema(
                id=img.id,
                filename=img.filename,
                original_filename=img.original_filename,
                storage_path=img.storage_path,
                content_type=img.content_type,
                file_size=img.file_size,
                width=img.width,
                height=img.height,
                file_hash=img.file_hash,
                status=img.status
            )

        # Fetch image metadata (for caption & tags)
        metadata = await metadata_repo.get_by_image_id(db, suggestion.image_id)
        generated_caption = metadata.caption if metadata else ""
        tags = metadata.tags if metadata else []

        # Fetch decision history
        decisions_list = await self.get_decisions_for_suggestion(db, suggestion.id)
        decision_responses = [
            ReviewDecisionResponse(
                id=d.id,
                suggestion_id=d.suggestion_id,
                reviewer_id=d.reviewer_id,
                action=d.action,
                notes=d.feedback_notes,
                created_at=d.created_at
            )
            for d in decisions_list
        ]
        latest_decision = decision_responses[0] if decision_responses else None

        # Build mismatch guard result schema
        guard_result = MismatchGuardResultSchema(
            guard_confidence_score=suggestion.guard_confidence_score,
            match_status=suggestion.match_status,
            reasoning=suggestion.match_reasoning
        )

        return ReviewResponse(
            id=suggestion.id,
            suggestion_id=suggestion.id,
            status=suggestion.review_status,
            post_id=suggestion.post_id,
            image_id=suggestion.image_id,
            similarity_score=suggestion.raw_similarity_score,
            raw_similarity_score=suggestion.raw_similarity_score,
            final_score=suggestion.final_score,
            rank=suggestion.rank,
            generated_caption=generated_caption,
            tags=tags,
            reason_for_recommendation=suggestion.match_reasoning,
            mismatch_guard_result=guard_result,
            image=img_schema,
            blog_post=post_schema,
            latest_decision=latest_decision,
            decisions=decision_responses,
            created_at=suggestion.created_at,
            updated_at=suggestion.updated_at
        )


review_repo = ReviewRepository()
