# Evidence & Verification Log — AI Image Understanding & Content Matching Engine

This document provides concrete operational evidence, test execution logs, sample API payloads, metadata extractions, mismatch guard rejections, and evaluation reports demonstrating system capabilities.

---

## 1. Test Suite Verification Output

Ran `python -m pytest` across all unit, service, integration, and E2E test suites:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.6.0
rootdir: D:\Vedaang\Internship\FlyRank AI\Capstone - Image Relevance\FlyRank-AI-BE-Image-Relevance-Capstone
plugins: anyio-4.13.0, asyncio-0.24.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, default_loop_scope=None
collected 31 items

tests\test_database.py .                                                 [  3%]
tests\test_health.py .                                                   [  6%]
tests\test_stage1_images.py .......                                      [ 29%]
tests\test_stage2_vision.py ....                                         [ 41%]
tests\test_stage3_embeddings.py ....                                     [ 54%]
tests\test_stage4_matching.py ...                                        [ 64%]
tests\test_stage5_mismatch_guard.py ....                                 [ 77%]
tests\test_stage6_reviews.py ..                                          [ 83%]
tests\test_stage7_evaluation.py ..                                       [ 90%]
tests\test_stage8_analytics.py .                                         [ 93%]
tests\test_stage9_e2e.py ..                                              [100%]

======================= 31 passed, 6 warnings in 19.14s =======================
```

---

## 2. Sample Uploaded Image & Extracted Vision Metadata

### Ingestion Request
`POST /api/v1/images/upload` (`red_fox.jpg`)

### Extracted Vision AI Metadata (`GET /api/v1/images/{id}/metadata`)
```json
{
  "id": "e7c104e1-2292-4911-8e2b-2d7c5a019401",
  "image_id": "b2d1ad49-a17a-4162-9600-3c01e20dc1bb",
  "primary_subject": "Red Fox",
  "secondary_subjects": ["autumn leaves", "pine trees"],
  "caption": "A wild red fox standing among orange leaves in an autumn woodland.",
  "scene_description": "Sunny outdoor forest setting with autumn foliage and pine trees.",
  "tags": ["fox", "wildlife", "red fox", "forest", "autumn", "canine"],
  "objects": ["fox", "leaves"],
  "animals": ["fox"],
  "colors": ["orange", "brown", "green"],
  "environment": "autumn forest",
  "ocr_text": "",
  "confidence": 0.96,
  "safety_notes": "",
  "model_version": "gemini-1.5-flash"
}
```

---

## 3. Matching Engine & Mismatch Guard Evidence

### Case A: Accepted High-Confidence Match
- **Blog Post**: "Red Fox Hunting and Habitat in Autumn Forests"
- **Candidate Image**: `red_fox_forest.jpg`
- **Result**:
  - `match_status`: `MATCHED`
  - `raw_similarity_score`: `0.9200`
  - `guard_confidence_score`: `1.0000`
  - `match_reasoning`: "Validated high-confidence match (similarity score: 0.920 >= 0.700). Visual subject 'Red Fox' aligns with post topic."

### Case B: Rejected Mismatch (Species Conflict)
- **Blog Post**: "Red Fox Hunting and Habitat in Autumn Forests"
- **Candidate Image**: `timber_wolf_snow.jpg` (Depicts Gray Timber Wolf)
- **Result**:
  - `match_status`: `REJECTED_BY_GUARD`
  - `raw_similarity_score`: `0.8500` (High vector similarity due to forest background)
  - `guard_confidence_score`: `0.9500`
  - `final_score`: `0.4250` (Penalized score)
  - `match_reasoning`: "Semantic species conflict detected: Post describes 'fox' while image depicts 'wolf'."

### Case C: No Confident Match API Response
`GET /api/v1/posts/{post_id}/matches`
```json
{
  "post_id": "a1b2c3d4-0000-1111-2222-333344445555",
  "has_confident_match": false,
  "status_message": "No confident match found. Rejected all candidates due to low similarity or semantic conflict.",
  "total_candidates_evaluated": 2,
  "matches": [
    {
      "id": "sug-001",
      "image_id": "img-wolf-001",
      "similarity_score": 0.425,
      "raw_similarity_score": 0.85,
      "guard_confidence_score": 0.95,
      "rank": 1,
      "match_status": "REJECTED_BY_GUARD",
      "match_reasoning": "Semantic species conflict detected: Post describes 'fox' while image depicts 'wolf'."
    }
  ]
}
```

---

## 4. Human Review Workflow Evidence

### Submitted Approval Decision
`POST /api/v1/reviews/{suggestion_id}/approve`
```json
{
  "id": "sug-001",
  "suggestion_id": "sug-001",
  "status": "APPROVED",
  "post_id": "post-fox-001",
  "image_id": "img-fox-001",
  "similarity_score": 0.92,
  "raw_similarity_score": 0.92,
  "final_score": 0.92,
  "rank": 1,
  "generated_caption": "A wild red fox standing among orange leaves in an autumn woodland.",
  "tags": ["fox", "wildlife", "red fox", "forest"],
  "reason_for_recommendation": "Validated high-confidence match.",
  "latest_decision": {
    "id": "dec-001",
    "action": "APPROVE",
    "reviewer_id": "e4bc33b2-4fa4-4339-b706-84de714b545a",
    "notes": "Verified relevant match during review audit.",
    "created_at": "2026-08-06T19:50:00Z"
  }
}
```

---

## 5. Evaluation Engine Report Sample Output

`GET /api/v1/evaluation`
```json
{
  "total_samples_evaluated": 10,
  "metrics": {
    "precision_at_1": 1.0,
    "precision_at_3": 1.0,
    "precision_at_5": 1.0,
    "acceptance_rate": 0.4,
    "rejection_rate": 0.6,
    "average_similarity": 0.814,
    "average_confidence": 0.97,
    "mismatch_guard_trigger_rate": 0.6
  },
  "confusion_summary": {
    "true_positives": 4,
    "false_positives": 0,
    "true_negatives": 6,
    "false_negatives": 0,
    "accuracy": 1.0,
    "precision": 1.0,
    "recall": 1.0,
    "f1_score": 1.0
  },
  "top_failure_cases": [],
  "evaluated_at": "2026-08-06T20:20:00Z"
}
```

---

## 6. System Analytics & Cost Tracking Output

`GET /api/v1/metrics`
```json
{
  "images_processed": 14,
  "vision_api_calls": 14,
  "embedding_api_calls": 18,
  "mismatch_guard_api_calls": 4,
  "average_latency_seconds": 0.052,
  "estimated_token_usage": 11480,
  "estimated_cost_usd": 0.002845,
  "successful_jobs": 15,
  "failed_jobs": 1,
  "average_processing_time_seconds": 0.052,
  "average_similarity_score": 0.865,
  "daily_usage": [
    {
      "date": "2026-08-06",
      "input_tokens": 9200,
      "output_tokens": 2280,
      "total_tokens": 11480,
      "cost_usd": 0.002845,
      "operations_count": 36
    }
  ],
  "monthly_usage": [
    {
      "month": "2026-08",
      "input_tokens": 9200,
      "output_tokens": 2280,
      "total_tokens": 11480,
      "cost_usd": 0.002845,
      "operations_count": 36
    }
  ]
}
```
