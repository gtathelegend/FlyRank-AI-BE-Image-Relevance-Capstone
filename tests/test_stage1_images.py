import io
import pytest
from pathlib import Path
from PIL import Image as PILImage
from httpx import AsyncClient
from app.core.config import settings


def create_dummy_image_bytes(width: int = 100, height: int = 100, fmt: str = "JPEG") -> bytes:
    """Helper to generate dummy image bytes in memory using Pillow."""
    img = PILImage.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_single_image_success(async_client: AsyncClient):
    """Test successful single image upload."""
    img_bytes = create_dummy_image_bytes(200, 150, "JPEG")
    files = {"file": ("test_upload.jpg", img_bytes, "image/jpeg")}

    response = await async_client.post("/api/v1/images/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["message"] == "Image uploaded successfully and background job queued."
    assert "job_id" in data
    img_data = data["image"]
    assert img_data["original_filename"] == "test_upload.jpg"
    assert img_data["width"] == 200
    assert img_data["height"] == 150
    assert img_data["status"] == "PENDING"

    # Verify file stored on disk
    stored_path = Path(img_data["stored_filename"])
    full_path = settings.STORAGE_IMAGES_DIR / stored_path
    assert full_path.exists()


@pytest.mark.asyncio
async def test_get_image_by_id(async_client: AsyncClient):
    """Test retrieving image metadata by ID."""
    img_bytes = create_dummy_image_bytes(120, 120, "PNG")
    files = {"file": ("fetch_test.png", img_bytes, "image/png")}

    upload_res = await async_client.post("/api/v1/images/upload", files=files)
    assert upload_res.status_code == 201
    img_id = upload_res.json()["image"]["id"]

    get_res = await async_client.get(f"/api/v1/images/{img_id}")
    assert get_res.status_code == 200
    fetched_data = get_res.json()
    assert fetched_data["id"] == img_id
    assert fetched_data["original_filename"] == "fetch_test.png"
    assert fetched_data["content_type"] == "image/png"


@pytest.mark.asyncio
async def test_list_images(async_client: AsyncClient):
    """Test listing catalog images with pagination."""
    img_bytes = create_dummy_image_bytes(100, 100, "JPEG")
    await async_client.post("/api/v1/images/upload", files={"file": ("list_1.jpg", img_bytes, "image/jpeg")})
    await async_client.post("/api/v1/images/upload", files={"file": ("list_2.jpg", img_bytes, "image/jpeg")})

    response = await async_client.get("/api/v1/images?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2



@pytest.mark.asyncio
async def test_upload_batch_images(async_client: AsyncClient):
    """Test uploading multiple images in a batch."""
    img1 = create_dummy_image_bytes(100, 100, "JPEG")
    img2 = create_dummy_image_bytes(300, 200, "PNG")

    files = [
        ("files", ("batch_1.jpg", img1, "image/jpeg")),
        ("files", ("batch_2.png", img2, "image/png"))
    ]

    response = await async_client.post("/api/v1/images/batch", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["total_uploaded"] == 2
    assert len(data["images"]) == 2
    assert "job_id" in data


@pytest.mark.asyncio
async def test_upload_invalid_format(async_client: AsyncClient):
    """Test error handling when uploading unsupported file format."""
    txt_bytes = b"This is a text file, not an image."
    files = {"file": ("document.txt", txt_bytes, "text/plain")}

    response = await async_client.post("/api/v1/images/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_corrupted_image(async_client: AsyncClient):
    """Test error handling when uploading corrupted image file."""
    corrupt_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF corrupted garbage bytes 12345"
    files = {"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")}

    response = await async_client.post("/api/v1/images/upload", files=files)
    assert response.status_code == 400
    assert "corrupted or unreadable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_oversized_file(async_client: AsyncClient):
    """Test error handling when file exceeds maximum size limit."""
    # Create 11MB dummy content
    large_bytes = b"0" * (11 * 1024 * 1024)
    files = {"file": ("huge_image.jpg", large_bytes, "image/jpeg")}

    response = await async_client.post("/api/v1/images/upload", files=files)
    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["detail"]
