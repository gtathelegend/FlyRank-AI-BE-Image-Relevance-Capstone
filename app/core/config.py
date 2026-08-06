from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Project Info
    PROJECT_NAME: str = "AI Image Understanding & Content Matching Engine"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "image_matching_db"
    DATABASE_URL: Union[str, None] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Union[str, None], info) -> str:
        if isinstance(v, str) and v:
            return v
        data = info.data
        user = data.get("POSTGRES_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD", "postgres")
        server = data.get("POSTGRES_SERVER", "localhost")
        port = data.get("POSTGRES_PORT", 5432)
        db = data.get("POSTGRES_DB", "image_matching_db")
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    # Sync DB URL for Alembic migrations
    @property
    def SYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url and url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url or f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security & JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production-1234567890"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # AI Provider Settings
    GEMINI_API_KEY: str = ""

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_BASE_DIR: Path = BASE_DIR / "storage"
    STORAGE_IMAGES_DIR: Path = STORAGE_BASE_DIR / "images"
    STORAGE_METADATA_DIR: Path = STORAGE_BASE_DIR / "metadata"
    STORAGE_EMBEDDINGS_DIR: Path = STORAGE_BASE_DIR / "embeddings"
    STORAGE_DATASETS_DIR: Path = STORAGE_BASE_DIR / "datasets"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # Mismatch Guard Thresholds
    MISMATCH_GUARD_MIN_SIMILARITY: float = 0.70
    MISMATCH_GUARD_MIN_CONFIDENCE: float = 0.80
    MISMATCH_GUARD_ENABLE_LLM_VALIDATION: bool = True

    LOG_LEVEL: str = "INFO"



settings = Settings()
