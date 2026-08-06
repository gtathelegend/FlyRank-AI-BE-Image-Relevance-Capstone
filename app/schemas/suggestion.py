from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.image import ImageResponse
from app.models.suggestion import MatchStatus


class SuggestionResponse(BaseModel):
    """API response schema for image match suggestions."""
    id: UUID
    post_id: UUID
    image_id: UUID
    image: Optional[ImageResponse] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Normalized similarity score between 0.0 and 1.0")
    raw_similarity_score: Optional[float] = None
    guard_confidence_score: Optional[float] = None
    rank: int = Field(..., ge=1, description="Top-K ranking position")
    match_status: MatchStatus
    match_reasoning: str
    is_reviewed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MatchResultsResponse(BaseModel):
    """Wrapper response schema for blog post matching results."""
    post_id: UUID
    has_confident_match: bool
    status_message: str
    total_candidates_evaluated: int
    matches: List[SuggestionResponse]
