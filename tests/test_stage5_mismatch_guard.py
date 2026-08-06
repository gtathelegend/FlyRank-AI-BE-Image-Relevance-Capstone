import io
import pytest
from PIL import Image as PILImage
from httpx import AsyncClient
from uuid import UUID
from app.services.mismatch_guard import mismatch_guard
from app.models.metadata import ImageMetadata
from app.models.suggestion import MatchStatus
from app.workers.post_worker import post_worker
from app.workers.vision_worker import vision_worker
from tests.conftest import TestingSessionLocal


class MockImageMetadata:
    def __init__(self, primary_subject: str, animals: list, environment: str, scene_description: str, tags: list):
        self.primary_subject = primary_subject
        self.animals = animals
        self.environment = environment
        self.scene_description = scene_description
        self.tags = tags


@pytest.mark.asyncio
async def test_mismatch_guard_species_conflict():
    """Test species conflict rejection (Fox vs Wolf, Dog vs Wolf)."""
    meta_wolf = MockImageMetadata(
        primary_subject="Gray Wolf",
        animals=["wolf"],
        environment="forest",
        scene_description="A wild timber wolf standing in a pine forest",
        tags=["wildlife", "predator"]
    )

    async with TestingSessionLocal() as db:
        # Fox post + Wolf image -> REJECT
        is_valid, conf, reason = await mismatch_guard.evaluate_candidate(
            db=db,
            post_title="Red Fox Habitat",
            post_content="Exploring the natural hunting territory of wild red fox species in autumn.",
            raw_similarity=0.85,
            image_metadata=meta_wolf
        )
        assert is_valid is False
        assert "species conflict" in reason.lower()

        # Dog post + Wolf image -> REJECT
        is_valid_dog, _, reason_dog = await mismatch_guard.evaluate_candidate(
            db=db,
            post_title="Domestic Dog Training Tips",
            post_content="How to train your pet dog for leash walking and home safety.",
            raw_similarity=0.82,
            image_metadata=meta_wolf
        )
        assert is_valid_dog is False
        assert "species conflict" in reason_dog.lower()


@pytest.mark.asyncio
async def test_mismatch_guard_environment_conflict():
    """Test environment conflict rejection (Forest vs City, Snow vs Desert)."""
    meta_city = MockImageMetadata(
        primary_subject="City Skyscraper",
        animals=[],
        environment="city",
        scene_description="Downtown city street with modern urban towers",
        tags=["building", "architecture"]
    )

    async with TestingSessionLocal() as db:
        # Forest post + City image -> REJECT
        is_valid, _, reason = await mismatch_guard.evaluate_candidate(
            db=db,
            post_title="Deep Forest Hiking Trails",
            post_content="Walking through dense pine woods and forest trees.",
            raw_similarity=0.80,
            image_metadata=meta_city
        )
        assert is_valid is False
        assert "environment conflict" in reason.lower()


@pytest.mark.asyncio
async def test_mismatch_guard_low_similarity_rejection():
    """Test low similarity score rejection (< 0.70 threshold)."""
    meta_any = MockImageMetadata(
        primary_subject="Random Object",
        animals=[],
        environment="room",
        scene_description="A room desk",
        tags=["furniture"]
    )

    async with TestingSessionLocal() as db:
        is_valid, _, reason = await mismatch_guard.evaluate_candidate(
            db=db,
            post_title="Quantum Physics Research",
            post_content="Theoretical developments in quantum mechanics and particle physics.",
            raw_similarity=0.45,  # Low score < 0.70
            image_metadata=meta_any
        )
        assert is_valid is False
        assert "below acceptance threshold" in reason.lower()


@pytest.mark.asyncio
async def test_mismatch_guard_end_to_end_no_confident_match(async_client: AsyncClient):
    """
    Test end-to-end API response returning 'No confident match' when candidates are rejected by Mismatch Guard.
    """
    # 1. Create Post about Arctic Snow Fox
    post_res = await async_client.post(
        "/api/v1/posts",
        json={
            "title": "Arctic Fox in Deep Snow",
            "content": "Surviving extreme sub-zero temperatures in frozen arctic snow environments.",
            "category": "Wildlife",
            "tags": ["fox", "arctic", "snow"]
        }
    )
    assert post_res.status_code == 201
    post_id = post_res.json()["post"]["id"]
    post_job = post_res.json()["job_id"]

    # 2. Upload mismatched Image (Desert City)
    buf = io.BytesIO()
    PILImage.new("RGB", (200, 200), "yellow").save(buf, format="JPEG")
    img_res = await async_client.post("/api/v1/images/upload", files={"file": ("desert_dunes.jpg", buf.getvalue(), "image/jpeg")})
    img_job = img_res.json()["job_id"]

    # 3. Execute background workers
    async with TestingSessionLocal() as db:
        await post_worker.process_post_embedding_job(db, UUID(post_job), UUID(post_id))
        await vision_worker.process_batch_job(db, UUID(img_job))

    # 4. Fetch matches via API
    matches_res = await async_client.get(f"/api/v1/posts/{post_id}/matches")
    assert matches_res.status_code == 200
    data = matches_res.json()

    assert str(data["post_id"]) == str(post_id)
    assert data["has_confident_match"] is False
    assert "no confident match" in data["status_message"].lower()

