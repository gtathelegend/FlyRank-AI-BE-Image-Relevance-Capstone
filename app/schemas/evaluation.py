from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MetricSummarySchema(BaseModel):
    """Core quantitative evaluation metrics for recommendations."""
    precision_at_1: float
    precision_at_3: float
    precision_at_5: float
    acceptance_rate: float
    rejection_rate: float
    average_similarity: float
    average_confidence: float
    mismatch_guard_trigger_rate: float

    model_config = ConfigDict(from_attributes=True)


class ConfusionSummarySchema(BaseModel):
    """Classification performance confusion matrix breakdown."""
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float

    model_config = ConfigDict(from_attributes=True)


class FailureCaseSchema(BaseModel):
    """Detailed error analysis record for predictions diverging from ground truth."""
    eval_id: str
    post_title: str
    image_filename: str
    predicted_match: bool
    ground_truth_match: bool
    error_type: str
    raw_similarity_score: float
    guard_confidence_score: float
    reasoning: str
    category_label: str

    model_config = ConfigDict(from_attributes=True)


class EvaluationReportResponse(BaseModel):
    """Full comprehensive evaluation report response."""
    total_samples_evaluated: int
    metrics: MetricSummarySchema
    confusion_summary: ConfusionSummarySchema
    top_failure_cases: List[FailureCaseSchema]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
