import hashlib
import io
import uuid
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image as PILImage
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
from app.core.logging import logger

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif"
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_DIMENSION_PX = 10  # 10x10 minimum dimensions


class StorageService:
    """Dedicated Image Storage and Validation Service."""

    def __init__(self, target_dir: Optional[Path] = None):
        self.target_dir = target_dir or settings.STORAGE_IMAGES_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def validate_file_format(self, content_type: str, filename: str) -> str:
        """Validates MIME type and file extension."""
        ext = Path(filename).suffix.lower()
        if content_type not in ALLOWED_MIME_TYPES and ext not in ALLOWED_MIME_TYPES.values():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{content_type}' or extension '{ext}'. Allowed: JPEG, PNG, WEBP, GIF."
            )
        return ext if ext in ALLOWED_MIME_TYPES.values() else ALLOWED_MIME_TYPES.get(content_type, ".jpg")

    def validate_file_size(self, file_size: int, filename: str) -> None:
        """Validates file size limit."""
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
            )
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' is empty (0 bytes)."
            )

    def validate_and_extract_dimensions(self, content: bytes, filename: str) -> Tuple[int, int]:
        """Validates image integrity and extracts width/height using Pillow."""
        try:
            image_stream = io.BytesIO(content)
            with PILImage.open(image_stream) as img:
                img.verify()
            
            # Re-open stream for dimension reading (verify consumes stream)
            image_stream.seek(0)
            with PILImage.open(image_stream) as img:
                width, height = img.size
                if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Image '{filename}' dimensions ({width}x{height}) below minimum required {MIN_DIMENSION_PX}x{MIN_DIMENSION_PX}px."
                    )
                return width, height
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Corrupted or unreadable image upload failure for '{filename}': {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image '{filename}' is corrupted or unreadable."
            )

    def compute_sha256(self, content: bytes) -> str:
        """Computes SHA-256 checksum hash of binary file content."""
        return hashlib.sha256(content).hexdigest()

    async def save_image(self, file: UploadFile) -> Tuple[bytes, str, str, Path, int, int, str]:
        """
        Reads, validates, computes hash, and saves file with unique UUID filename.
        Returns (content, original_filename, stored_filename, storage_path, width, height, file_hash).
        """
        original_filename = file.filename or "uploaded_image.jpg"
        logger.info(f"Upload started for file '{original_filename}'")

        try:
            content = await file.read()
            file_size = len(content)

            # Validate format, size, corruption & dimensions
            ext = self.validate_file_format(file.content_type or "", original_filename)
            self.validate_file_size(file_size, original_filename)
            width, height = self.validate_and_extract_dimensions(content, original_filename)

            # Compute hash checksum
            file_hash = self.compute_sha256(content)

            # Generate unique stored filename
            unique_id = uuid.uuid4().hex
            stored_filename = f"{unique_id}{ext}"
            file_path = self.target_dir / stored_filename

            # Never overwrite existing file
            if file_path.exists():
                stored_filename = f"{unique_id}_{uuid.uuid4().hex[:6]}{ext}"
                file_path = self.target_dir / stored_filename

            # Save content to disk
            with open(file_path, "wb") as f:
                f.write(content)

            logger.info(f"Upload completed: '{original_filename}' saved as '{stored_filename}' at {file_path}")
            return content, original_filename, stored_filename, file_path, width, height, file_hash

        except Exception as e:
            if not isinstance(e, HTTPException):
                logger.error(f"Storage failure saving file '{original_filename}': {e}")
            raise


storage_service = StorageService()
