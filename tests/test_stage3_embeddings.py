import io
import pytest
from PIL import Image as PILImage
from httpx import AsyncClient
from uuid import UUID
from app.models.post import BlogPost, PostStatus
from app.models.job import JobStatus
from app.services.embedding_pipeline import embedding_pipeline
from app.workers.post_worker import post_worker
from app.workers.vision_worker import vision_worker
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_embedding_pipeline_direct():
    """Test direct vector embedding generation for text inputs."""
    text = "Artificial Intelligence and Machine Learning in modern backend architecture."
    vector, tokens = await embedding_pipeline.generate_embedding_with_retry(text)

    assert isinstance(vector, list)
    assert len(vector) == 768
    assert tokens > 0


@pytest.mark.asyncio
async def test_create_blog_post_validation(async_client: AsyncClient):
    """Test blog post creation input validation rules."""
    # 1. Empty content rejection
    res_empty = await async_client.post(
        "/api/v1/posts",
        json={"title": "Valid Title", "content": "   "}
    )
    assert res_empty.status_code == 422 or res_empty.status_code == 400

    # 2. Too short content rejection (< 10 chars)
    res_short = await async_client.post(
        "/api/v1/posts",
        json={"title": "Valid Title", "content": "Short"}
    )
    assert res_short.status_code == 422 or res_short.status_code == 400

    # 3. Missing title rejection
    res_no_title = await async_client.post(
        "/api/v1/posts",
        json={"title": "   ", "content": "This is a valid long blog post content body."}
    )
    assert res_no_title.status_code == 422 or res_no_title.status_code == 400


@pytest.mark.asyncio
async def test_create_blog_post_and_generate_embeddings(async_client: AsyncClient):
    """Test blog post creation and background worker embedding execution."""
    post_payload = {
        "title": "Understanding Modern Cloud Architecture",
        "content": "Deep dive into microservices, containerization with Docker, and automated deployment pipelines.",
        "author": "Tech Lead",
        "category": "Engineering",
        "summary": "Overview of modern cloud infrastructure design patterns.",
        "tags": ["cloud", "docker", "architecture"]
    }

    # 1. Create post via API
    res = await async_client.post("/api/v1/posts", json=post_payload)
    assert res.status_code == 201
    data = res.json()
    post_id = data["post"]["id"]
    job_id = data["job_id"]

    # 2. Run post worker processing directly
    async with TestingSessionLocal() as db:
        completed_job = await post_worker.process_post_embedding_job(db, UUID(job_id), UUID(post_id))
        assert completed_job.status == JobStatus.COMPLETED

    # 3. Get post details & verify INDEXED status
    post_res = await async_client.get(f"/api/v1/posts/{post_id}")
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "INDEXED"

    # 4. Get post embedding details
    emb_res = await async_client.get(f"/api/v1/posts/{post_id}/embedding")
    assert emb_res.status_code == 200
    emb_data = emb_res.json()
    assert emb_data["dimension"] == 768
    assert emb_data["model_name"] == "text-embedding-004"


@pytest.mark.asyncio
async def test_image_pipeline_includes_embeddings(async_client: AsyncClient):
    """Test that image vision worker generates image vector embeddings."""
    buf = io.BytesIO()
    PILImage.new("RGB", (180, 180), "purple").save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    upload_res = await async_client.post("/api/v1/images/upload", files={"file": ("embed_img.jpg", img_bytes, "image/jpeg")})
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    img_id = upload_data["image"]["id"]
    job_id = upload_data["job_id"]

    # Execute vision + embedding worker
    async with TestingSessionLocal() as db:
        completed_job = await vision_worker.process_batch_job(db, UUID(job_id))
        assert completed_job.status == JobStatus.COMPLETED

    # Verify image embedding metadata endpoint
    emb_res = await async_client.get(f"/api/v1/images/{img_id}/embedding")
    assert emb_res.status_code == 200
    emb_data = emb_res.json()
    assert emb_data["image_id"] == img_id
    assert emb_data["dimension"] == 768
    assert emb_data["status"] == "COMPLETED"
