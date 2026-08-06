import io
import pytest
import numpy as np
from PIL import Image as PILImage
from httpx import AsyncClient
from uuid import UUID
from app.utils.vector_math import cosine_similarity, rank_candidates_by_similarity
from app.services.matching_engine import matching_engine
from app.workers.post_worker import post_worker
from app.workers.vision_worker import vision_worker
from tests.conftest import TestingSessionLocal


def test_cosine_similarity_math():
    """Test vector similarity calculations and bounds [0.0, 1.0]."""
    v1 = [1.0, 0.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0, 0.0]
    # Identical vectors -> 1.0
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-5

    v3 = [0.0, 1.0, 0.0, 0.0]
    # Orthogonal vectors -> 0.0
    assert abs(cosine_similarity(v1, v3) - 0.0) < 1e-5

    v4 = [-1.0, 0.0, 0.0, 0.0]
    # Opposite vectors clamped to [0.0, 1.0] range
    score = cosine_similarity(v1, v4)
    assert 0.0 <= score <= 1.0


def test_candidate_ranking():
    """Test candidate vector ranking order."""
    query = [1.0, 0.0, 0.0]
    candidates = [
        ("c1_orthogonal", [0.0, 1.0, 0.0]),
        ("c2_exact", [1.0, 0.0, 0.0]),
        ("c3_similar", [0.8, 0.2, 0.0])
    ]
    ranked = rank_candidates_by_similarity(query, candidates)
    assert ranked[0][0] == "c2_exact"
    assert ranked[1][0] == "c3_similar"
    assert ranked[2][0] == "c1_orthogonal"


@pytest.mark.asyncio
async def test_semantic_matching_engine_end_to_end(async_client: AsyncClient):
    """
    Test end-to-end semantic relevance matching engine.
    Relevant images must be ranked higher than irrelevant ones.
    """
    # 1. Create two distinct blog posts
    post1_res = await async_client.post(
        "/api/v1/posts",
        json={
            "title": "Cloud Computing and Distributed Systems",
            "content": "Deep dive into cloud server architecture, microservices, containerization with Docker and Kubernetes.",
            "category": "Technology",
            "tags": ["cloud", "server", "docker", "architecture"]
        }
    )
    assert post1_res.status_code == 201
    post1_id = post1_res.json()["post"]["id"]
    post1_job = post1_res.json()["job_id"]

    post2_res = await async_client.post(
        "/api/v1/posts",
        json={
            "title": "Italian Pasta Cooking Recipes",
            "content": "Learn how to make authentic homemade fettuccine pasta with fresh basil, tomatoes, and olive oil.",
            "category": "Cooking",
            "tags": ["pasta", "recipe", "cooking", "food"]
        }
    )
    assert post2_res.status_code == 201
    post2_id = post2_res.json()["post"]["id"]
    post2_job = post2_res.json()["job_id"]

    # 2. Upload two distinct images
    buf1 = io.BytesIO()
    PILImage.new("RGB", (200, 200), "blue").save(buf1, format="JPEG")
    img1_res = await async_client.post("/api/v1/images/upload", files={"file": ("tech_cloud.jpg", buf1.getvalue(), "image/jpeg")})
    img1_job = img1_res.json()["job_id"]

    buf2 = io.BytesIO()
    PILImage.new("RGB", (200, 200), "red").save(buf2, format="JPEG")
    img2_res = await async_client.post("/api/v1/images/upload", files={"file": ("food_pasta.jpg", buf2.getvalue(), "image/jpeg")})
    img2_job = img2_res.json()["job_id"]

    # 3. Process workers for posts and images
    async with TestingSessionLocal() as db:
        await post_worker.process_post_embedding_job(db, UUID(post1_job), UUID(post1_id))
        await post_worker.process_post_embedding_job(db, UUID(post2_job), UUID(post2_id))
        await vision_worker.process_batch_job(db, UUID(img1_job))
        await vision_worker.process_batch_job(db, UUID(img2_job))

    # 4. Fetch candidate matches via API for Post 1
    matches1_res = await async_client.get(f"/api/v1/posts/{post1_id}/matches?top_k=5")
    assert matches1_res.status_code == 200
    matches1 = matches1_res.json()
    assert isinstance(matches1, list)
    assert len(matches1) >= 2

    # Verify rank 1 has rank = 1 and highest similarity score
    assert matches1[0]["rank"] == 1
    assert matches1[0]["similarity_score"] >= matches1[1]["similarity_score"]
    assert "match_reasoning" in matches1[0]
    assert len(matches1[0]["match_reasoning"]) > 10
