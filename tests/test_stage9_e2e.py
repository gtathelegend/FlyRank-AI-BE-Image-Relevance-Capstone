import io
import pytest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch
from PIL import Image as PILImage
from httpx import AsyncClient
from uuid import UUID
from sqlalchemy import select

from app.models.image import Image, ImageStatus
from app.models.job import BatchJob, JobStatus, JobType
from app.models.post import BlogPost, PostStatus
from app.models.suggestion import Suggestion, MatchStatus, ReviewStatus
from app.models.review import ReviewDecision, ReviewAction
from app.workers.vision_worker import vision_worker
from app.workers.post_worker import post_worker
from tests.conftest import TestingSessionLocal


def generate_test_image_bytes(color: str = "blue", width: int = 150, height: int = 150) -> bytes:
    """Utility helper generating JPEG image bytes in memory."""
    buf = io.BytesIO()
    PILImage.new("RGB", (width, height), color=color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_full_system_e2e_integration_flow(async_client: AsyncClient):
    """
    Comprehensive End-to-End Integration Test covering:
    1. Single & Batch Image Upload
    2. AI Vision Processing & Metadata Generation
    3. Image Vector Embedding Pipeline
    4. Blog Post Creation
    5. Post Embedding Pipeline
    6. Semantic Relevance Matching Engine & Mismatch Guard
    7. Human Review Workflow (Approve & Reject with notes)
    8. Evaluation Framework Report & Metrics
    9. System Analytics & Cost Tracking Dashboard
    """
    reviewer_id = str(uuid.uuid4())

    # --- 1. Image Upload (Single & Batch) ---
    img1_bytes = generate_test_image_bytes("red", 200, 200)
    img2_bytes = generate_test_image_bytes("green", 200, 200)

    # Single Upload
    upload1_res = await async_client.post(
        "/api/v1/images/upload",
        files={"file": ("red_fox.jpg", img1_bytes, "image/jpeg")}
    )
    assert upload1_res.status_code == 201
    img1_id = upload1_res.json()["image"]["id"]
    job1_id = upload1_res.json()["job_id"]

    # Batch Upload
    files_batch = [
        ("files", ("green_forest.jpg", img2_bytes, "image/jpeg")),
    ]
    upload2_res = await async_client.post("/api/v1/images/batch", files=files_batch)
    assert upload2_res.status_code == 201
    job2_id = upload2_res.json()["job_id"]

    # --- 2. Vision & Embedding Background Processing ---
    async with TestingSessionLocal() as db:
        await vision_worker.process_batch_job(db, UUID(job1_id))
        await vision_worker.process_batch_job(db, UUID(job2_id))

    # Verify Image Metadata extracted
    meta_res = await async_client.get(f"/api/v1/images/{img1_id}/metadata")
    assert meta_res.status_code == 200
    assert meta_res.json()["image_id"] == img1_id

    # Verify Image Embedding generated
    emb_res = await async_client.get(f"/api/v1/images/{img1_id}/embedding")
    assert emb_res.status_code == 200
    assert emb_res.json()["dimension"] == 768

    # --- 3. Blog Post Creation & Embedding Processing ---
    post_res = await async_client.post(
        "/api/v1/posts",
        json={
            "title": "Wildlife Exploration: Red Fox in Autumn Forest",
            "content": "Exploring the natural hunting territory and forest biomes of red foxes in autumn.",
            "category": "Nature",
            "tags": ["fox", "forest", "wildlife"]
        }
    )
    assert post_res.status_code == 201
    post_id = post_res.json()["post"]["id"]
    post_job_id = post_res.json()["job_id"]

    async with TestingSessionLocal() as db:
        await post_worker.process_post_embedding_job(db, UUID(post_job_id), UUID(post_id))

    # Verify Post Embedding generated
    post_emb_res = await async_client.get(f"/api/v1/posts/{post_id}/embedding")
    assert post_emb_res.status_code == 200
    assert post_emb_res.json()["post_id"] == post_id

    # --- 4. Semantic Matching & Mismatch Guard ---
    matches_res = await async_client.get(f"/api/v1/posts/{post_id}/matches")
    assert matches_res.status_code == 200
    matches_data = matches_res.json()
    assert matches_data["post_id"] == post_id
    assert len(matches_data["matches"]) >= 1

    sug_id = matches_data["matches"][0]["id"]

    # --- 5. Human Review Workflow ---
    # List reviews
    reviews_res = await async_client.get("/api/v1/reviews")
    assert reviews_res.status_code == 200
    assert reviews_res.json()["total"] >= 1

    # Inspect single review
    rev_detail = await async_client.get(f"/api/v1/reviews/{sug_id}")
    assert rev_detail.status_code == 200
    assert rev_detail.json()["id"] == sug_id

    # Approve match with notes
    app_res = await async_client.post(
        f"/api/v1/reviews/{sug_id}/approve",
        json={
            "reviewer_id": reviewer_id,
            "notes": "Verified relevant match during E2E integration test."
        }
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"

    # --- 6. Evaluation Framework Metrics ---
    eval_report = await async_client.get("/api/v1/evaluation")
    assert eval_report.status_code == 200
    assert eval_report.json()["total_samples_evaluated"] >= 3

    eval_metrics = await async_client.get("/api/v1/evaluation/metrics")
    assert eval_metrics.status_code == 200
    assert "precision_at_1" in eval_metrics.json()

    # --- 7. Cost Tracking & Analytics Dashboard ---
    sys_metrics = await async_client.get("/api/v1/metrics")
    assert sys_metrics.status_code == 200
    assert sys_metrics.json()["images_processed"] >= 1

    cost_metrics = await async_client.get("/api/v1/metrics/cost")
    assert cost_metrics.status_code == 200
    assert cost_metrics.json()["total_tokens"] > 0

    job_metrics = await async_client.get("/api/v1/metrics/jobs")
    assert job_metrics.status_code == 200
    assert job_metrics.json()["total_jobs"] >= 3


@pytest.mark.asyncio
async def test_failure_modes_and_edge_cases(async_client: AsyncClient):
    """
    Tests failure handling for:
    - Unsupported file format
    - Corrupted image bytes
    - Empty/invalid blog post data
    - Vision API failure handling in background worker
    - Embedding API failure handling in background worker
    - Low similarity candidate rejection
    """

    # 1. Unsupported File Format Upload
    res_unsupported = await async_client.post(
        "/api/v1/images/upload",
        files={"file": ("document.pdf", b"%PDF-1.4 dummy pdf content", "application/pdf")}
    )
    assert res_unsupported.status_code == 400
    assert "Unsupported file format" in res_unsupported.json()["detail"]

    # 2. Corrupted Image Upload
    corrupt_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF corrupted binary data 9999"
    res_corrupt = await async_client.post(
        "/api/v1/images/upload",
        files={"file": ("corrupted.jpg", corrupt_bytes, "image/jpeg")}
    )
    assert res_corrupt.status_code == 400
    assert "corrupted or unreadable" in res_corrupt.json()["detail"]

    # 3. Empty / Invalid Blog Post Creation
    res_empty_title = await async_client.post(
        "/api/v1/posts",
        json={
            "title": "   ",  # Whitespace title
            "content": "Valid content body text long enough."
        }
    )
    assert res_empty_title.status_code == 422

    res_short_content = await async_client.post(
        "/api/v1/posts",
        json={
            "title": "Valid Title",
            "content": "Short"  # Content under 10 chars
        }
    )
    assert res_short_content.status_code == 422

    # 4. Vision API Failure Handling in Worker
    img_bytes = generate_test_image_bytes("blue", 100, 100)
    upload_res = await async_client.post(
        "/api/v1/images/upload",
        files={"file": ("vision_fail_test.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    fail_job_id = upload_res.json()["job_id"]

    with patch("app.services.vision_pipeline.vision_pipeline.process_image_vision", side_effect=RuntimeError("AI Vision API Service Failure")):
        async with TestingSessionLocal() as db:
            completed_job = await vision_worker.process_batch_job(db, UUID(fail_job_id))
            assert completed_job.status == JobStatus.FAILED
            assert "errors" in completed_job.error_details

    # 5. Embedding API Failure Handling in Worker
    async with TestingSessionLocal() as db:
        post_fail = BlogPost(
            title="Embedding Failure Test Post",
            content="Testing embedding pipeline failure handling and error state recording.",
            category="Testing",
            status=PostStatus.PENDING
        )
        db.add(post_fail)
        await db.commit()
        await db.refresh(post_fail)

        job_fail = BatchJob(
            job_type=JobType.BATCH_EMBEDDING,
            status=JobStatus.PENDING,
            total_items=1
        )
        db.add(job_fail)
        await db.commit()
        await db.refresh(job_fail)

        post_fail_id = post_fail.id
        post_fail_job_id = job_fail.id

    with patch("app.services.embedding_pipeline.embedding_pipeline.generate_and_store_post_embedding", side_effect=RuntimeError("Embedding API Timeout")):
        async with TestingSessionLocal() as db:
            with pytest.raises(RuntimeError, match="Embedding API Timeout"):
                await post_worker.process_post_embedding_job(db, post_fail_job_id, post_fail_id)

            failed_job = await db.get(BatchJob, post_fail_job_id)
            assert failed_job.status == JobStatus.FAILED
            assert "errors" in failed_job.error_details or "error" in failed_job.error_details


    # 6. Low Similarity / Semantic Conflict Match Rejection
    # Create Quantum Physics Post
    q_post_res = await async_client.post(
        "/api/v1/posts",
        json={
            "title": "Quantum Electrodynamics and Particle Physics",
            "content": "Theoretical research on quantum subatomic particle accelerations.",
            "category": "Physics"
        }
    )
    q_post_id = q_post_res.json()["post"]["id"]
    q_job_id = q_post_res.json()["job_id"]

    # Upload unrelated furniture image
    furn_res = await async_client.post(
        "/api/v1/images/upload",
        files={"file": ("furniture_desk.jpg", img_bytes, "image/jpeg")}
    )
    furn_job_id = furn_res.json()["job_id"]

    async with TestingSessionLocal() as db:
        await post_worker.process_post_embedding_job(db, UUID(q_job_id), UUID(q_post_id))
        await vision_worker.process_batch_job(db, UUID(furn_job_id))

    matches_res = await async_client.get(f"/api/v1/posts/{q_post_id}/matches")
    assert matches_res.status_code == 200
    m_data = matches_res.json()
    assert m_data["has_confident_match"] is False
    assert "no confident match" in m_data["status_message"].lower()
