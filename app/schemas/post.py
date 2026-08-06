from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.models.post import PostStatus


class BlogPostCreate(BaseModel):
    """Pydantic schema for blog post creation requests."""
    title: str = Field(..., min_length=1, max_length=255, description="Blog post title")
    content: str = Field(..., min_length=10, description="Full blog post content body")
    author: Optional[str] = Field(None, max_length=255, description="Optional author name")
    category: Optional[str] = Field(None, max_length=100, description="Optional category classification")
    summary: Optional[str] = Field(None, description="Optional short summary")
    tags: List[str] = Field(default_factory=list, description="List of topic tags")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Blog post title cannot be empty or whitespace only.")
        return s

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Blog post content cannot be empty or whitespace only.")
        if len(s) < 10:
            raise ValueError("Blog post content is too short (minimum 10 characters required).")
        return s


class BlogPostResponse(BaseModel):
    """Pydantic schema for blog post response details."""
    id: UUID
    title: str
    content: str
    author: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str]
    status: PostStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SinglePostCreateResponse(BaseModel):
    """API response schema for blog post creation endpoint."""
    message: str = "Blog post created successfully and embedding generation queued."
    post: BlogPostResponse
    job_id: UUID


class ImageEmbeddingResponse(BaseModel):
    """Schema for Image embedding details."""
    id: UUID
    image_id: UUID
    dimension: int
    model_name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PostEmbeddingResponse(BaseModel):
    """Schema for Post embedding details."""
    id: UUID
    post_id: UUID
    dimension: int
    model_name: str
    created_at: datetime

    class Config:
        from_attributes = True
