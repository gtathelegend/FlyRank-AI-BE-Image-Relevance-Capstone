# Build Log — AI Image Understanding & Content Matching Engine

## Development Timeline & Phases

### Stage 0: Initial Engine Setup & Infrastructure
- **Phase Objective**: Initialize repository, setup directory structure, configure FastAPI application shell, configure async SQLAlchemy engine with Alembic migrations, and setup logging & environment configuration.
- **Key Artifacts**: `app/main.py`, `app/core/config.py`, `app/core/database.py`, `alembic/versions/001_stage0_initial_models.py`.

### Stage 1: Image Ingestion Pipeline
- **Phase Objective**: Build upload endpoints (`/images/upload` and `/images/batch`), file validation (size, content type, SHA-256 hash deduplication), local disk storage, and database persistence.
- **Key Artifacts**: `app/api/v1/images.py`, `app/services/storage_service.py`, `alembic/versions/002_stage1_image_dimensions.py`.

### Stage 2: AI Vision Processing Pipeline
- **Phase Objective**: Integrate Google Gemini 1.5 Flash Vision AI to extract structured JSON metadata (caption, scene description, tags, objects, animals, environment) with Pydantic validation, exponential backoff retries, and asynchronous background worker processing.
- **Key Artifacts**: `app/services/vision_pipeline.py`, `app/workers/vision_worker.py`, `app/schemas/vision.py`, `alembic/versions/003_stage2_image_metadata.py`.

### Stage 3: Semantic Vector Embedding Pipeline
- **Phase Objective**: Implement multimodal embedding generation using Google `text-embedding-004` (768-dimensional float vectors) for catalog images and blog posts with weighted chunk aggregation.
- **Key Artifacts**: `app/services/embedding_pipeline.py`, `app/repositories/embedding_repo.py`, `alembic/versions/004_stage3_embeddings_and_posts.py`.

### Stage 4: Semantic Relevance Engine
- **Phase Objective**: Build cosine vector similarity search engine matching blog post embeddings against catalog image vector embeddings, ranking Top-K candidate matches.
- **Key Artifacts**: `app/services/matching_engine.py`, `app/utils/vector_math.py`, `alembic/versions/005_stage4_suggestions.py`.

### Stage 5: Mismatch Guard Guardrail System
- **Phase Objective**: Implement multi-tier precision guardrails enforcing similarity thresholding (`MISMATCH_GUARD_MIN_SIMILARITY = 0.70`), species conflict detection (Fox vs Wolf, Dog vs Wolf, Cat vs Lion), and biome/environment conflict detection (Forest vs City, Snow vs Desert). Prefer "No confident match" over misleading matches.
- **Key Artifacts**: `app/services/mismatch_guard.py`, `tests/test_stage5_mismatch_guard.py`.

### Stage 6: Human Review Workflow (HITL)
- **Phase Objective**: Build human review system (`GET /reviews`, `GET /reviews/{id}`, `POST /reviews/{id}/approve`, `POST /reviews/{id}/reject`) allowing human reviewers to inspect matches, approve/reject recommendations, provide notes, and audit review decisions.
- **Key Artifacts**: `app/api/v1/reviews.py`, `app/repositories/review_repo.py`, `alembic/versions/006_stage6_reviews.py`.

### Stage 7: Quantitative Evaluation Engine
- **Phase Objective**: Implement evaluation metrics suite calculating Precision@1, Precision@3, Precision@5, Acceptance Rate, Rejection Rate, Average Similarity, Average Confidence, Mismatch Guard Trigger Rate, Confusion Matrix (TP, FP, TN, FN, Accuracy, F1), and top failure cases.
- **Key Artifacts**: `app/services/evaluation_engine.py`, `storage/datasets/eval_dataset.json`, `app/api/v1/evaluation.py`.

### Stage 8: Cost Tracking & Analytics Dashboard
- **Phase Objective**: Build operational analytics and cost tracking endpoints (`GET /metrics`, `GET /metrics/cost`, `GET /metrics/jobs`) tracking processed images, API call counts, token usage, estimated USD costs, job success/failure counts, latency, and daily/monthly trends.
- **Key Artifacts**: `app/services/analytics_service.py`, `app/api/v1/metrics.py`, `alembic/versions/007_stage8_analytics_indexes.py`.

### Stage 9: End-to-End Automated Integration Testing
- **Phase Objective**: Create comprehensive automated integration tests covering the complete end-to-end flow and edge-case failure modes (invalid image, corrupted image, unsupported format, empty blog, Vision API failure, Embedding API failure, low similarity rejection).
- **Key Artifacts**: `tests/test_stage9_e2e.py`.

### Stage 10: Documentation & Final Submission
- **Phase Objective**: Finalize capstone documentation, build logs, architectural design documents, capstone metadata manifest, docker configuration, environment setup, and submission verification.

---

## AI Assistance Used
- **Gemini 3.6 Flash / Antigravity Agentic Pair Programming**: Autonomous code generation, refactoring, test suite creation, Alembic migration drafting, and architectural documentation.

---

## Problems Encountered & Solutions Implemented

### Problem 1: SQLite vs PostgreSQL pgvector Compatibility in Testing
- **Issue**: Production database uses PostgreSQL with `pgvector`, whereas fast unit/integration tests run against SQLite in-memory/file databases which do not natively support pgvector vector types.
- **Solution**: Designed vector storage using JSON column serialization for embeddings in model abstractions while storing 768-dimensional float arrays, enabling seamless cross-platform execution on both SQLite and PostgreSQL.

### Problem 2: Preserving Precision with Mismatch Guard
- **Issue**: Standard vector cosine similarity alone produced false-positive matches for visually similar but semantically conflicting entities (e.g., Red Fox post matching a Timber Wolf image due to high background forest similarity).
- **Solution**: Developed a multi-tier **Mismatch Guard** that inspects AI-extracted vision metadata for species conflicts (e.g. `fox` vs `wolf`) and biome conflicts (e.g. `forest` vs `city`) to penalize or reject misleading matches, favoring "No confident match" when precision is compromised.

### Problem 3: Background Worker Async Event Loop Execution in FastAPITests
- **Issue**: Background tasks dispatched via FastAPI `BackgroundTasks` in tests created separate async tasks that occasionally competed for database session locks.
- **Solution**: Structured background worker functions to accept explicit database sessions (`AsyncSession`), ensuring test fixtures can cleanly run background processing sequentially and deterministically.
