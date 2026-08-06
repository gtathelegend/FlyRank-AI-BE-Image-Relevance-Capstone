import io
import pytest
from pathlib import Path
from PIL import Image as PILImage
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.image import Image, ImageStatus
from app.models.job import BatchJob, JobStatus
from app.models.metadata import ImageMetadata
from app.models.cost import CostLog, OperationType
from app.services.vision_pipeline import vision_pipeline, StructuredVisionResponse
from app.workers.vision_worker import vision_worker


def create_sample_image_file(target_dir: Path, name: str = "sample_vision.jpg") -> Path:
    """Helper creating a sample JPEG image file on disk."""
    target_dir.mkdir(parents=True, exist_ok=True)
    img_path = target_dir / name
    img = PILImage.new("RGB", (250, 200), color="green")
    img.save(img_path, format="JPEG")
    return img_path


@pytest.mark.asyncio
async def test_vision_pipeline_direct_processing(tmp_path: Path):
    """Test direct vision pipeline execution and structured output generation."""
    img_path = create_sample_image_file(tmp_path, "direct_test.jpg")
    
    result, input_tokens, output_tokens = await vision_pipeline.analyze_image_with_retry(img_path)
    
    assert isinstance(result, StructuredVisionResponse)
    assert result.primary_subject is not None
    assert isinstance(result.tags, list)
    assert len(result.tags) >= 3
    assert 0.0 <= result.confidence <= 1.0
    assert input_tokens > 0
    assert output_tokens > 0


@pytest.mark.asyncio
async def test_json_parsing_and_pydantic_validation():
    """Test parsing raw JSON response and rejecting malformed inputs."""
    valid_json = """{
        "primary_subject": "Laptop on desk",
        "secondary_subjects": ["coffee cup"],
        "caption": "A modern laptop sitting on a wooden desk.",
        "scene_description": "Clean office setup with natural lighting.",
        "tags": ["laptop", "desk", "office", "work"],
        "objects": ["laptop", "desk", "cup"],
        "animals": [],
        "colors": ["brown", "silver"],
        "environment": "Office",
        "ocr_text": "",
        "confidence": 0.98,
        "safety_notes": ""
    }"""
    parsed = vision_pipeline._parse_and_validate_json(valid_json)
    assert parsed.primary_subject == "Laptop on desk"
    assert parsed.confidence == 0.98

    # Malformed JSON test
    invalid_json = '{"primary_subject": "Broken JSON", "tags": ['
    with pytest.raises(ValueError, match="Malformed JSON"):
        vision_pipeline._parse_and_validate_json(invalid_json)

    # Missing required field test (missing caption & environment)
    missing_fields_json = '{"primary_subject": "Incomplete"}'
    with pytest.raises(ValueError, match="validation failed"):
        vision_pipeline._parse_and_validate_json(missing_fields_json)


@pytest.mark.asyncio
async def test_worker_process_batch_job(async_client: AsyncClient, prepare_database):
    """Test worker processing a queued batch job and persisting metadata + cost logs."""
    # 1. Upload two images via API
    buf = io.BytesIO()
    PILImage.new("RGB", (100, 100), "red").save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    files = [
        ("files", ("worker_img1.jpg", img_bytes, "image/jpeg")),
        ("files", ("worker_img2.jpg", img_bytes, "image/jpeg"))
    ]
    upload_res = await async_client.post("/api/v1/images/batch", files=files)
    assert upload_res.status_code == 201
    job_id = upload_res.json()["job_id"]

    # 2. Trigger worker processing via API
    process_res = await async_client.post(f"/api/v1/jobs/{job_id}/process")
    assert process_res.status_code == 202

    # 3. Check Job Status endpoint
    status_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()
    assert job_data["id"] == job_id


@pytest.mark.asyncio
async def test_full_worker_execution_flow(async_client: AsyncClient):
    """Test full execution of vision_worker processing image to completion."""
    # Upload image
    buf = io.BytesIO()
    PILImage.new("RGB", (150, 150), "yellow").save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    upload_res = await async_client.post("/api/v1/images/upload", files={"file": ("full_flow.jpg", img_bytes, "image/jpeg")})
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    img_id = upload_data["image"]["id"]
    job_id = upload_data["job_id"]

    # Verify image metadata before processing (should 404)
    meta_pre = await async_client.get(f"/api/v1/images/{img_id}/metadata")
    assert meta_pre.status_code == 404

    # Trigger worker execution directly
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as db:
        from uuid import UUID
        completed_job = await vision_worker.process_batch_job(db, UUID(job_id))
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.processed_items == 1



    # Verify image metadata post-processing (should 200 OK)
    meta_post = await async_client.get(f"/api/v1/images/{img_id}/metadata")
    assert meta_post.status_code == 200
    meta_data = meta_post.json()
    assert meta_data["image_id"] == img_id
    assert "primary_subject" in meta_data
    assert len(meta_data["tags"]) > 0
