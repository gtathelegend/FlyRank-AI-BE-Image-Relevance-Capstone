from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.suggestion import MatchStatus, ReviewStatus
from app.models.review import ReviewAction


class ReviewDecisionCreate(BaseModel):
    """Payload for submitting a human review approval or rejection decision."""
    reviewer_id: Optional[UUID] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewDecisionResponse(BaseModel):
    """Recorded review decision audit trail item."""
    id: UUID
    suggestion_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    action: ReviewAction
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageReviewSchema(BaseModel):
    """Image catalog metadata embedded within review data."""
    id: UUID
    filename: str
    original_filename: str
    storage_path: str
    content_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    file_hash: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class BlogPostReviewSchema(BaseModel):
    """Blog post target content embedded within review data."""
    id: UUID
    title: str
    content: str
    author: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    status: str

    model_config = ConfigDict(from_attributes=True)


class MismatchGuardResultSchema(BaseModel):
    """Mismatch Guard check details for human inspection."""
    guard_confidence_score: Optional[float] = None
    match_status: MatchStatus
    reasoning: str

    model_config = ConfigDict(from_attributes=True)


class ReviewResponse(BaseModel):
    """Comprehensive review item representation for UI and API consumers."""
    id: UUID
    suggestion_id: UUID
    status: ReviewStatus
    post_id: UUID
    image_id: UUID
    similarity_score: float
    raw_similarity_score: float
    final_score: float
    rank: int
    generated_caption: str
    tags: List[str]
    reason_for_recommendation: str
    mismatch_guard_result: MismatchGuardResultSchema
    image: Optional[ImageReviewSchema] = None
    blog_post: Optional[BlogPostReviewSchema] = None
    latest_decision: Optional[ReviewDecisionResponse] = None
    decisions: List[ReviewDecisionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """Paginated response containing review items and metadata count."""
    total: int
    items: List[ReviewResponse]
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
