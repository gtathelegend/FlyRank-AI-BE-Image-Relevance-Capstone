import pytest
from httpx import AsyncClient
from app.services.evaluation_engine import evaluation_engine
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_evaluation_engine_service():
    """Test evaluation engine dataset loading and metric calculations."""
    dataset = evaluation_engine.load_dataset()
    assert len(dataset) >= 3

    # Check dataset entries contain required ground truth fields
    for item in dataset:
        assert "id" in item
        assert "is_relevant_ground_truth" in item
        assert "category_label" in item
        assert "post_title" in item
        assert "image_primary_subject" in item

    async with TestingSessionLocal() as db:
        report = await evaluation_engine.run_evaluation(db)

        # Check total evaluated sample count
        assert report.total_samples_evaluated == len(dataset)

        # Verify metrics presence and range
        m = report.metrics
        assert 0.0 <= m.precision_at_1 <= 1.0
        assert 0.0 <= m.precision_at_3 <= 1.0
        assert 0.0 <= m.precision_at_5 <= 1.0
        assert 0.0 <= m.acceptance_rate <= 1.0
        assert 0.0 <= m.rejection_rate <= 1.0
        assert 0.0 <= m.average_similarity <= 1.0
        assert 0.0 <= m.average_confidence <= 1.0
        assert 0.0 <= m.mismatch_guard_trigger_rate <= 1.0

        # Verify confusion summary breakdown
        c = report.confusion_summary
        assert c.true_positives + c.false_positives + c.true_negatives + c.false_negatives == len(dataset)
        assert 0.0 <= c.accuracy <= 1.0
        assert 0.0 <= c.precision <= 1.0
        assert 0.0 <= c.recall <= 1.0
        assert 0.0 <= c.f1_score <= 1.0


@pytest.mark.asyncio
async def test_evaluation_api_endpoints(async_client: AsyncClient):
    """Test GET /api/v1/evaluation and GET /api/v1/evaluation/metrics endpoints."""
    # 1. Test GET /api/v1/evaluation (Full Report)
    res_report = await async_client.get("/api/v1/evaluation")
    assert res_report.status_code == 200
    data_report = res_report.json()

    assert "total_samples_evaluated" in data_report
    assert "metrics" in data_report
    assert "confusion_summary" in data_report
    assert "top_failure_cases" in data_report
    assert "evaluated_at" in data_report

    metrics = data_report["metrics"]
    assert "precision_at_1" in metrics
    assert "precision_at_3" in metrics
    assert "precision_at_5" in metrics
    assert "acceptance_rate" in metrics
    assert "rejection_rate" in metrics
    assert "average_similarity" in metrics
    assert "average_confidence" in metrics
    assert "mismatch_guard_trigger_rate" in metrics

    # 2. Test GET /api/v1/evaluation/metrics (Concise Metrics)
    res_metrics = await async_client.get("/api/v1/evaluation/metrics")
    assert res_metrics.status_code == 200
    data_metrics = res_metrics.json()

    assert "precision_at_1" in data_metrics
    assert "precision_at_3" in data_metrics
    assert "precision_at_5" in data_metrics
    assert "acceptance_rate" in data_metrics
    assert "rejection_rate" in data_metrics
    assert "average_similarity" in data_metrics
    assert "average_confidence" in data_metrics
    assert "mismatch_guard_trigger_rate" in data_metrics
