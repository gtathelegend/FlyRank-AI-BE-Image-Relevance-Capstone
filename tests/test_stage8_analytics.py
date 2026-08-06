import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from decimal import Decimal

from app.models.image import Image, ImageStatus
from app.models.job import BatchJob, JobStatus, JobType
from app.models.cost import CostLog, OperationType
from app.models.post import BlogPost
from app.models.suggestion import Suggestion, MatchStatus, ReviewStatus
from app.services.analytics_service import analytics_service
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_stage8_analytics_workload_and_api(async_client: AsyncClient):
    """
    Generates a sample workload and verifies /metrics, /metrics/cost, and /metrics/jobs endpoints.
    """
    async with TestingSessionLocal() as db:
        # 1. Create processed images
        img1 = Image(
            filename="nature_1.jpg",
            original_filename="nature_1.jpg",
            stored_filename="stored_nature_1.jpg",
            storage_path="/tmp/n1.jpg",
            content_type="image/jpeg",
            file_size=50000,
            status=ImageStatus.PROCESSED
        )
        img2 = Image(
            filename="nature_2.jpg",
            original_filename="nature_2.jpg",
            stored_filename="stored_nature_2.jpg",
            storage_path="/tmp/n2.jpg",
            content_type="image/jpeg",
            file_size=60000,
            status=ImageStatus.PROCESSED
        )
        db.add_all([img1, img2])
        await db.commit()

        # 2. Create batch jobs (1 completed, 1 failed)
        job1 = BatchJob(
            job_type=JobType.IMAGE_INDEXING,
            status=JobStatus.COMPLETED,
            total_items=2,
            processed_items=2
        )
        job2 = BatchJob(
            job_type=JobType.POST_MATCHING,
            status=JobStatus.FAILED,
            total_items=1,
            processed_items=0,
            error_details={"error": "Test failure"}
        )
        db.add_all([job1, job2])
        await db.commit()
        await db.refresh(job1)

        # 3. Create cost logs for Vision, Embedding, and Guard operations
        c1 = CostLog(
            operation_type=OperationType.VISION_ANALYSIS,
            model_name="gemini-1.5-flash",
            input_tokens=500,
            output_tokens=100,
            estimated_cost_usd=Decimal("0.000067"),
            job_id=job1.id
        )
        c2 = CostLog(
            operation_type=OperationType.EMBEDDING_GEN,
            model_name="text-embedding-004",
            input_tokens=200,
            output_tokens=0,
            estimated_cost_usd=Decimal("0.000005"),
            job_id=job1.id
        )
        c3 = CostLog(
            operation_type=OperationType.MISMATCH_GUARD_VERIFICATION,
            model_name="gemini-1.5-flash",
            input_tokens=180,
            output_tokens=50,
            estimated_cost_usd=Decimal("0.000028"),
            job_id=job1.id
        )
        db.add_all([c1, c2, c3])
        await db.commit()

        # 4. Create a blog post and match suggestion with similarity score
        post = BlogPost(
            title="Nature Adventure Guide",
            content="Exploring green forests and outdoor nature trails.",
            category="Nature"
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)

        sug = Suggestion(
            post_id=post.id,
            image_id=img1.id,
            raw_similarity_score=0.88,
            guard_confidence_score=1.0,
            final_score=0.88,
            rank=1,
            match_status=MatchStatus.MATCHED,
            match_reasoning="High relevance match.",
            is_reviewed=False,
            review_status=ReviewStatus.PENDING
        )
        db.add(sug)
        await db.commit()

    # 5. Test GET /api/v1/metrics
    res_metrics = await async_client.get("/api/v1/metrics")
    assert res_metrics.status_code == 200
    data_sys = res_metrics.json()

    assert data_sys["images_processed"] >= 2
    assert data_sys["vision_api_calls"] >= 1
    assert data_sys["embedding_api_calls"] >= 1
    assert data_sys["mismatch_guard_api_calls"] >= 1
    assert data_sys["estimated_token_usage"] >= 980
    assert data_sys["estimated_cost_usd"] > 0.0
    assert data_sys["successful_jobs"] >= 1
    assert data_sys["failed_jobs"] >= 1
    assert data_sys["average_similarity_score"] > 0.0
    assert len(data_sys["daily_usage"]) >= 1
    assert len(data_sys["monthly_usage"]) >= 1

    # 6. Test GET /api/v1/metrics/cost
    res_cost = await async_client.get("/api/v1/metrics/cost")
    assert res_cost.status_code == 200
    data_cost = res_cost.json()

    assert data_cost["estimated_cost_usd"] > 0.0
    assert data_cost["total_tokens"] >= 980
    assert "VISION_ANALYSIS" in data_cost["cost_by_operation"]
    assert "EMBEDDING_GEN" in data_cost["cost_by_operation"]
    assert "gemini-1.5-flash" in data_cost["cost_by_model"]
    assert len(data_cost["daily_usage"]) >= 1

    # 7. Test GET /api/v1/metrics/jobs
    res_jobs = await async_client.get("/api/v1/metrics/jobs")
    assert res_jobs.status_code == 200
    data_jobs = res_jobs.json()

    assert data_jobs["total_jobs"] >= 2
    assert data_jobs["successful_jobs"] >= 1
    assert data_jobs["failed_jobs"] >= 1
    assert 0.0 <= data_jobs["success_rate"] <= 1.0
    assert "IMAGE_INDEXING" in data_jobs["jobs_by_type"]
