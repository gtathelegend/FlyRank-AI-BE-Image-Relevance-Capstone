import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Test that the health endpoint returns 200 and expected JSON structure."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["app_name"] == "AI Image Understanding & Content Matching Engine"
    assert data["environment"] == "development"
    assert "timestamp" in data
