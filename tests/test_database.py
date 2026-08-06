import pytest
from app.models.image import Image, ImageStatus
from app.models.job import BatchJob, JobType, JobStatus
from app.models.cost import CostLog, OperationType
from app.models.review import ReviewDecision, ReviewAction


def test_model_instantiation():
    """Verify that Stage 0 ORM models instantiate correctly."""
    img = Image(
        filename="sample_test.jpg",
        storage_path="storage/images/sample_test.jpg",
        content_type="image/jpeg",
        file_size=1024,
        status=ImageStatus.PENDING
    )
    assert img.filename == "sample_test.jpg"
    assert img.status == ImageStatus.PENDING

    job = BatchJob(
        job_type=JobType.IMAGE_INDEXING,
        status=JobStatus.PENDING,
        total_items=10
    )
    assert job.job_type == JobType.IMAGE_INDEXING
    assert job.total_items == 10

    cost = CostLog(
        operation_type=OperationType.VISION_ANALYSIS,
        model_name="gemini-1.5-flash",
        input_tokens=150,
        output_tokens=50,
        estimated_cost_usd=0.00025
    )
    assert cost.operation_type == OperationType.VISION_ANALYSIS
    assert cost.estimated_cost_usd == 0.00025

    review = ReviewDecision(
        action=ReviewAction.APPROVE,
        feedback_notes="Looks great!"
    )
    assert review.action == ReviewAction.APPROVE
