from datetime import datetime
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Schema for health check response endpoint."""
    status: str = Field(default="ok", json_schema_extra={"example": "ok"})
    app_name: str = Field(..., json_schema_extra={"example": "AI Image Understanding & Content Matching Engine"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    version: str = Field(default="0.1.0", json_schema_extra={"example": "0.1.0"})
    timestamp: datetime
    database: str = Field(default="connected", json_schema_extra={"example": "connected"})

