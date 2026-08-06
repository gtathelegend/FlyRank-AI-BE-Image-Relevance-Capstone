from typing import Optional
from datetime import date, datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.suggestion import ReviewStatus
from app.models.review import ReviewAction
from app.repositories.review_repo import review_repo
from app.schemas.review import (
    ReviewResponse,
    ReviewListResponse,
    ReviewDecisionCreate
)

router = APIRouter()


@router.get(
    "",
    response_model=ReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List review candidates",
    description="Retrieve paginated review records supporting filtering by status, image, post, and creation date."
)
async def list_reviews(
    review_status: Optional[ReviewStatus] = Query(None, alias="status", description="Filter by review status: PENDING, APPROVED, REJECTED"),
    image_id: Optional[UUID] = Query(None, description="Filter by catalog image UUID"),
    post_id: Optional[UUID] = Query(None, description="Filter by blog post UUID"),
    review_date: Optional[date] = Query(None, alias="date", description="Filter by specific creation date (YYYY-MM-DD)"),
    start_date: Optional[datetime] = Query(None, description="Filter by creation start timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter by creation end timestamp"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Pagination page limit"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search and filter human review candidates.
    """
    logger.info(
        f"Querying reviews: status={review_status}, image_id={image_id}, post_id={post_id}, "
        f"date={review_date}, skip={skip}, limit={limit}"
    )
    suggestions, total = await review_repo.get_reviews(
        db=db,
        status=review_status,
        image_id=image_id,
        post_id=post_id,
        review_date=review_date,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )

    items = []
    for s in suggestions:
        resp = await review_repo.build_review_response(db, s)
        items.append(resp)

    return ReviewListResponse(
        total=total,
        items=items,
        skip=skip,
        limit=limit
    )


@router.get(
    "/{id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single review item details",
    description="Inspect complete details of an AI-generated match suggestion."
)
async def get_review(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves full details for a specific review item by suggestion ID.
    Logs review opened event.
    """
    logger.info(f"Review opened for suggestion_id={id}")
    suggestion = await review_repo.get_suggestion(db, id)
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item with ID '{id}' not found."
        )

    return await review_repo.build_review_response(db, suggestion)


@router.post(
    "/{id}/approve",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve match suggestion",
    description="Approve an AI-generated image recommendation with optional reviewer notes."
)
async def approve_review(
    id: UUID,
    payload: Optional[ReviewDecisionCreate] = Body(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Approves a review candidate, persisting decision state and reviewer notes.
    """
    suggestion = await review_repo.get_suggestion(db, id)
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item with ID '{id}' not found."
        )

    reviewer_id = payload.reviewer_id if payload else None
    notes = payload.notes if payload else None

    logger.info(f"Suggestion approved for suggestion_id={id}, reviewer_id={reviewer_id}")
    if notes:
        logger.info(f"Reviewer notes for suggestion_id={id}: {notes}")

    updated_suggestion, decision = await review_repo.record_decision(
        db=db,
        suggestion=suggestion,
        action=ReviewAction.APPROVE,
        reviewer_id=reviewer_id,
        notes=notes
    )

    return await review_repo.build_review_response(db, updated_suggestion)


@router.post(
    "/{id}/reject",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject match suggestion",
    description="Reject an AI-generated image recommendation with optional reviewer notes."
)
async def reject_review(
    id: UUID,
    payload: Optional[ReviewDecisionCreate] = Body(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Rejects a review candidate, persisting decision state and reviewer notes.
    """
    suggestion = await review_repo.get_suggestion(db, id)
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item with ID '{id}' not found."
        )

    reviewer_id = payload.reviewer_id if payload else None
    notes = payload.notes if payload else None

    logger.info(f"Suggestion rejected for suggestion_id={id}, reviewer_id={reviewer_id}")
    if notes:
        logger.info(f"Reviewer notes for suggestion_id={id}: {notes}")

    updated_suggestion, decision = await review_repo.record_decision(
        db=db,
        suggestion=suggestion,
        action=ReviewAction.REJECT,
        reviewer_id=reviewer_id,
        notes=notes
    )

    return await review_repo.build_review_response(db, updated_suggestion)
