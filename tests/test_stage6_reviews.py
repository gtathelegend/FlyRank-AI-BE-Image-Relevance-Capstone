import io
import pytest
import uuid
from datetime import date
from PIL import Image as PILImage
from httpx import AsyncClient
from uuid import UUID
from sqlalchemy import select

from app.models.suggestion import Suggestion, MatchStatus, ReviewStatus
from app.models.review import ReviewDecision, ReviewAction
from app.models.post import BlogPost
from app.models.image import Image, ImageStatus
from app.models.metadata import ImageMetadata
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_stage6_human_review_workflow(async_client: AsyncClient):
    """
    Complete end-to-end integration test for Stage 6 Human Review Workflow.
    - Create test post, images, metadata, and suggestions.
    - Test GET /reviews (list, filtering by status, date, image_id).
    - Test GET /reviews/{id} (inspect single review item details).
    - Test POST /reviews/{id}/approve (approve with notes & reviewer_id).
    - Test POST /reviews/{id}/reject (reject with notes & reviewer_id).
    - Verify database persistence.
    """
    reviewer_uuid = uuid.uuid4()

    async with TestingSessionLocal() as db:
        # 1. Create a blog post
        post = BlogPost(
            title="Golden Retriever Care Guide",
            content="Tips on feeding, grooming, and training golden retriever dogs.",
            category="Pets",
            tags=["dog", "golden retriever", "pets"]
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)

        # 2. Create Image 1 (Golden Retriever) and Image 2 (Cat)
        img1 = Image(
            filename="golden_retriever.jpg",
            original_filename="golden_retriever.jpg",
            stored_filename="stored_golden.jpg",
            storage_path="/tmp/golden.jpg",
            content_type="image/jpeg",
            file_size=102400,
            width=800,
            height=600,
            status=ImageStatus.PROCESSED
        )
        img2 = Image(
            filename="persian_cat.jpg",
            original_filename="persian_cat.jpg",
            stored_filename="stored_cat.jpg",
            storage_path="/tmp/cat.jpg",
            content_type="image/jpeg",
            file_size=98000,
            width=800,
            height=600,
            status=ImageStatus.PROCESSED
        )
        db.add_all([img1, img2])
        await db.commit()
        await db.refresh(img1)
        await db.refresh(img2)

        # 3. Create Image Metadata for both images
        meta1 = ImageMetadata(
            image_id=img1.id,
            primary_subject="Golden Retriever Dog",
            secondary_subjects=["dog leash", "grass"],
            caption="A happy golden retriever sitting in a sunny park",
            scene_description="Sunny park setting with green grass and outdoor dog playground",
            tags=["dog", "canine", "golden retriever", "pet"],
            objects=["dog", "leash"],
            animals=["dog"],
            colors=["golden", "green"],
            environment="outdoor park"
        )
        meta2 = ImageMetadata(
            image_id=img2.id,
            primary_subject="Persian Cat",
            secondary_subjects=["cushion"],
            caption="A fluffy white Persian cat sleeping on a sofa",
            scene_description="Indoor living room setting with soft cushions",
            tags=["cat", "feline", "persian cat", "pet"],
            objects=["cat", "sofa"],
            animals=["cat"],
            colors=["white", "beige"],
            environment="indoor living room"
        )
        db.add_all([meta1, meta2])
        await db.commit()

        # 4. Create Suggestion 1 (Matched) and Suggestion 2 (Rejected by Guard)
        sug1 = Suggestion(
            post_id=post.id,
            image_id=img1.id,
            raw_similarity_score=0.92,
            guard_confidence_score=1.0,
            final_score=0.92,
            rank=1,
            match_status=MatchStatus.MATCHED,
            match_reasoning="High similarity match: Golden Retriever aligns with dog post content.",
            is_reviewed=False,
            review_status=ReviewStatus.PENDING
        )
        sug2 = Suggestion(
            post_id=post.id,
            image_id=img2.id,
            raw_similarity_score=0.75,
            guard_confidence_score=0.95,
            final_score=0.375,
            rank=2,
            match_status=MatchStatus.REJECTED_BY_GUARD,
            match_reasoning="Species conflict detected: Post describes 'dog' while image depicts 'cat'.",
            is_reviewed=False,
            review_status=ReviewStatus.PENDING
        )
        db.add_all([sug1, sug2])
        await db.commit()
        await db.refresh(sug1)
        await db.refresh(sug2)

        sug1_id = str(sug1.id)
        sug2_id = str(sug2.id)
        img1_id = str(img1.id)
        post_id = str(post.id)

    # 5. GET /api/v1/reviews - List all reviews (should return 2 pending)
    res_list = await async_client.get("/api/v1/reviews")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["total"] == 2
    assert len(data_list["items"]) == 2

    # Verify review data fields
    item1 = next(item for item in data_list["items"] if item["id"] == sug1_id)
    assert item1["status"] == "PENDING"
    assert item1["similarity_score"] == 0.92
    assert item1["generated_caption"] == "A happy golden retriever sitting in a sunny park"
    assert "golden retriever" in item1["tags"]
    assert "High similarity match" in item1["reason_for_recommendation"]
    assert item1["mismatch_guard_result"]["match_status"] == "MATCHED"
    assert item1["image"]["filename"] == "golden_retriever.jpg"
    assert item1["blog_post"]["title"] == "Golden Retriever Care Guide"

    # 6. GET /api/v1/reviews/{id} - Get single review detail
    res_single = await async_client.get(f"/api/v1/reviews/{sug1_id}")
    assert res_single.status_code == 200
    single_data = res_single.json()
    assert single_data["id"] == sug1_id
    assert single_data["image_id"] == img1_id
    assert single_data["post_id"] == post_id

    # 7. POST /api/v1/reviews/{id}/approve - Approve sug1
    approve_res = await async_client.post(
        f"/api/v1/reviews/{sug1_id}/approve",
        json={
            "reviewer_id": str(reviewer_uuid),
            "notes": "Excellent match! Approved for publication."
        }
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["status"] == "APPROVED"
    assert approved_data["latest_decision"]["action"] == "APPROVE"
    assert approved_data["latest_decision"]["notes"] == "Excellent match! Approved for publication."
    assert approved_data["latest_decision"]["reviewer_id"] == str(reviewer_uuid)

    # 8. POST /api/v1/reviews/{id}/reject - Reject sug2
    reject_res = await async_client.post(
        f"/api/v1/reviews/{sug2_id}/reject",
        json={
            "reviewer_id": str(reviewer_uuid),
            "notes": "Correctly rejected species conflict (cat for dog post)."
        }
    )
    assert reject_res.status_code == 200
    rejected_data = reject_res.json()
    assert rejected_data["status"] == "REJECTED"
    assert rejected_data["latest_decision"]["action"] == "REJECT"

    # 9. Test filtering by status (APPROVED)
    res_approved = await async_client.get("/api/v1/reviews?status=APPROVED")
    assert res_approved.status_code == 200
    data_approved = res_approved.json()
    assert data_approved["total"] == 1
    assert data_approved["items"][0]["id"] == sug1_id

    # Test filtering by status (REJECTED)
    res_rejected = await async_client.get("/api/v1/reviews?status=REJECTED")
    assert res_rejected.status_code == 200
    data_rejected = res_rejected.json()
    assert data_rejected["total"] == 1
    assert data_rejected["items"][0]["id"] == sug2_id

    # Test filtering by image_id
    res_img = await async_client.get(f"/api/v1/reviews?image_id={img1_id}")
    assert res_img.status_code == 200
    assert res_img.json()["total"] == 1
    assert res_img.json()["items"][0]["image_id"] == img1_id

    # Test filtering by date (today's date)
    today_str = date.today().isoformat()
    res_date = await async_client.get(f"/api/v1/reviews?date={today_str}")
    assert res_date.status_code == 200
    assert res_date.json()["total"] == 2

    # 10. Verify Database State
    async with TestingSessionLocal() as db:
        # Check suggestions state in DB
        s1 = await db.scalar(select(Suggestion).where(Suggestion.id == UUID(sug1_id)))
        assert s1.is_reviewed is True
        assert s1.review_status == ReviewStatus.APPROVED

        s2 = await db.scalar(select(Suggestion).where(Suggestion.id == UUID(sug2_id)))
        assert s2.is_reviewed is True
        assert s2.review_status == ReviewStatus.REJECTED

        # Check review_decisions records in DB
        decisions_s1 = (await db.scalars(select(ReviewDecision).where(ReviewDecision.suggestion_id == UUID(sug1_id)))).all()
        assert len(decisions_s1) == 1
        assert decisions_s1[0].action == ReviewAction.APPROVE
        assert decisions_s1[0].feedback_notes == "Excellent match! Approved for publication."

        decisions_s2 = (await db.scalars(select(ReviewDecision).where(ReviewDecision.suggestion_id == UUID(sug2_id)))).all()
        assert len(decisions_s2) == 1
        assert decisions_s2[0].action == ReviewAction.REJECT


@pytest.mark.asyncio
async def test_review_not_found(async_client: AsyncClient):
    """Test 404 response for non-existent review IDs."""
    fake_id = str(uuid.uuid4())

    res_get = await async_client.get(f"/api/v1/reviews/{fake_id}")
    assert res_get.status_code == 404

    res_app = await async_client.post(f"/api/v1/reviews/{fake_id}/approve")
    assert res_app.status_code == 404

    res_rej = await async_client.post(f"/api/v1/reviews/{fake_id}/reject")
    assert res_rej.status_code == 404
