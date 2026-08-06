from typing import List, Optional
from pydantic import BaseModel, Field


class StructuredVisionResponse(BaseModel):
    """Pydantic schema enforcing structured JSON output from Gemini Flash Vision."""
    primary_subject: str = Field(
        ...,
        description="The main focal subject of the image (e.g., 'Golden Retriever dog')"
    )
    secondary_subjects: List[str] = Field(
        default_factory=list,
        description="Secondary objects or contextual elements present in the background or side"
    )
    caption: str = Field(
        ...,
        description="A concise, factual 1-2 sentence caption summarizing the image content"
    )
    scene_description: str = Field(
        ...,
        description="Detailed objective description of the visual scene, composition, lighting, and layout"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of relevant, searchable semantic tags (lowercase, 5-15 tags)"
    )
    objects: List[str] = Field(
        default_factory=list,
        description="List of distinct inanimate physical objects identified in the image"
    )
    animals: List[str] = Field(
        default_factory=list,
        description="List of animals or living species identified in the image"
    )
    colors: List[str] = Field(
        default_factory=list,
        description="List of dominant visual colors (e.g., ['ocean blue', 'warm orange', 'white'])"
    )
    environment: str = Field(
        ...,
        description="Setting or environment type (e.g., 'Indoor office', 'Outdoor forest', 'Studio background')"
    )
    ocr_text: Optional[str] = Field(
        default="",
        description="Any readable text extracted inside the image via optical character recognition"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence score of visual analysis between 0.0 and 1.0"
    )
    safety_notes: Optional[str] = Field(
        default="",
        description="Any safety, sensitive content, or quality notes if applicable"
    )


class ImageMetadataResponse(BaseModel):
    """API response schema for ImageMetadata."""
    id: str
    image_id: str
    primary_subject: str
    secondary_subjects: List[str]
    caption: str
    scene_description: str
    tags: List[str]
    objects: List[str]
    animals: List[str]
    colors: List[str]
    environment: str
    ocr_text: Optional[str] = ""
    confidence: float
    safety_notes: Optional[str] = ""
    model_version: str
    created_at: str

    class Config:
        from_attributes = True
