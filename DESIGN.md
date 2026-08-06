# Technical System Design Document
## AI Image Understanding & Content Matching Engine

### 1. Executive Summary
The **AI Image Understanding & Content Matching Engine** is an enterprise-grade backend platform built to automatically analyze catalog images using computer vision AI, generate multimodal vector embeddings, match visual assets to target blog posts using cosine vector similarity, enforce precision guardrails via a multi-tier **Mismatch Guard**, provide a **Human-in-the-Loop Review Workflow**, evaluate system quality using quantitative benchmark metrics (Precision@K), and track operational costs and API token consumption in real time.

---

### 2. High-Level System Architecture

```
                                  +-----------------------+
                                  |    Client / UI / API  |
                                  +-----------+-----------+
                                              |
                                              v
                                   +----------+----------+
                                   | FastAPI REST Gateway|
                                   +----------+----------+
                                              |
       +--------------------+-----------------+--------------------+--------------------+
       |                    |                 |                    |                    |
       v                    v                 v                    v                    v
+--------------+   +-----------------+ +-------------+   +-------------------+ +---------------+
| Image        |   | Vision AI       | | Embedding   |   | Mismatch Guard    | | Review &      |
| Ingestion    |   | Pipeline        | | Pipeline    |   | Service           | | Evaluation    |
+--------------+   +-----------------+ +-------------+   +-------------------+ +---------------+
       |                    |                 |                    |                    |
       v                    v                 v                    v                    v
+-----------------------------------------------------------------------------------------------+
|                               PostgreSQL Database + pgvector                                  |
| (images, image_metadata, image_embeddings, blog_posts, post_embeddings, suggestions, review)  |
+-----------------------------------------------------------------------------------------------+
```

---

### 3. Core Component Architecture

#### 3.1 Image Ingestion & Storage Service (`app/services/storage_service.py`)
- Accepts single file uploads (`POST /images/upload`) and batch uploads (`POST /images/batch`).
- Computes SHA-256 content hashes to detect duplicate image uploads.
- Validates file headers, dimensions using Pillow, and content size (max 10 MB).
- Saves images to disk under immutable UUID storage filenames (`storage/images/`).
- Dispatches asynchronous background processing jobs (`BatchJob`).

#### 3.2 Vision AI Processing Pipeline (`app/services/vision_pipeline.py`)
- Integrates with Google Gemini 1.5 Flash Vision AI model.
- Uses strict prompt engineering to produce deterministic JSON output containing:
  - `primary_subject`, `secondary_subjects`
  - `caption` (concise objective summary)
  - `scene_description` (lighting, layout, background)
  - `tags` (5–15 searchable semantic tags)
  - `objects`, `animals`, `colors`, `environment`, `ocr_text`, `confidence`
- Validates JSON output with Pydantic (`StructuredVisionResponse`).
- Includes automatic exponential backoff retries and structured mock fallbacks for testing.
- Logs API token consumption and USD cost.

#### 3.3 Semantic Embedding Pipeline (`app/services/embedding_pipeline.py`)
- Uses Google `text-embedding-004` (768-dimensional float vectors).
- Generates image embeddings from combined visual subject, caption, scene description, tags, and environment text.
- Generates post embeddings by creating weighted text chunks for:
  - Title & Category
  - Summary / Excerpt
  - Full Post Body Content
- Combines chunk embeddings into a single unified 768-dimensional vector representation.
- Stores vector embeddings in PostgreSQL `image_embeddings` and `post_embeddings` tables with pgvector support.

#### 3.4 Semantic Relevance Matching Engine (`app/services/matching_engine.py`)
- Given a target blog post ID:
  1. Fetches candidate catalog image embeddings.
  2. Computes cosine similarity between post vector and image vectors.
  3. Ranks candidates by descending raw similarity score.
  4. Evaluates Top-K candidates through **Mismatch Guard**.
  5. Stores recommendations in `suggestions` table.
  6. Prefers "No confident match" if top candidates fail guard verification or fall below the similarity threshold (`MISMATCH_GUARD_MIN_SIMILARITY = 0.70`).

#### 3.5 Mismatch Guard System (`app/services/mismatch_guard.py`)
Enforces strict precision and prevents misleading image matches using a multi-tiered rule engine:
- **Tier 1 (Similarity Threshold Check)**: Rejects candidates with raw similarity score below `0.70`.
- **Tier 2 (Species / Entity Conflict Rule)**: Rejects candidate if post describes one animal (e.g. Fox) while image depicts a conflicting species (e.g. Wolf, Dog, Cat, Lion).
- **Tier 3 (Environment / Biome Conflict Rule)**: Rejects candidate if post describes one environment (e.g. Forest) while image depicts an incompatible biome (e.g. City skyscraper, Desert dunes, Ocean).
- **Tier 4 (LLM Guard Verification)**: Optional secondary LLM verification for live production deployments.

#### 3.6 Human Review Workflow (`app/repositories/review_repo.py` & `app/api/v1/reviews.py`)
- Provides human-in-the-loop review capabilities (`GET /reviews`, `GET /reviews/{id}`).
- Allows human reviewers to inspect full match details (Image, Blog Post, similarity score, caption, tags, match reasoning, mismatch guard result).
- Reviewers approve (`POST /reviews/{id}/approve`) or reject (`POST /reviews/{id}/reject`) candidates with optional reviewer ID and feedback notes.
- Audit trail recorded in `review_decisions` table.

#### 3.7 Evaluation Engine (`app/services/evaluation_engine.py`)
- Evaluates recommendation quality across a benchmark dataset (`storage/datasets/eval_dataset.json`).
- Calculates key metrics:
  - `Precision@1`, `Precision@3`, `Precision@5`
  - `Acceptance Rate` & `Rejection Rate`
  - `Average Similarity` & `Average Confidence`
  - `Mismatch Guard Trigger Rate`
  - Confusion Matrix (`True Positives`, `False Positives`, `True Negatives`, `False Negatives`, `Accuracy`, `F1 Score`)
  - `Top Failure Cases` error analysis.

#### 3.8 Analytics & Cost Tracking Engine (`app/services/analytics_service.py`)
- Tracks total images processed, Vision API calls, Embedding API calls, Mismatch Guard calls, token consumption (input/output), and estimated USD cost.
- Aggregates job execution statistics (successful/failed jobs, success rates, average latency).
- Computes time-series daily usage and monthly usage trends.

---

### 4. Database Schema & Data Models

- **`images`**: `id`, `filename`, `original_filename`, `stored_filename`, `storage_path`, `content_type`, `file_size`, `width`, `height`, `file_hash`, `status`, `created_at`, `updated_at`.
- **`batch_jobs`**: `id`, `job_type`, `status`, `total_items`, `processed_items`, `error_details`, `created_at`, `updated_at`.
- **`image_metadata`**: `id`, `image_id` (FK), `primary_subject`, `secondary_subjects`, `caption`, `scene_description`, `tags`, `objects`, `animals`, `colors`, `environment`, `ocr_text`, `confidence`, `safety_notes`, `model_version`.
- **`image_embeddings`**: `id`, `image_id` (FK), `embedding` (JSON/Vector 768-dim), `model_name`, `dimension`, `status`.
- **`blog_posts`**: `id`, `title`, `content`, `author`, `category`, `summary`, `tags`, `status`.
- **`post_embeddings`**: `id`, `post_id` (FK), `title_embedding`, `summary_embedding`, `content_embedding`, `combined_vector` (Vector 768-dim), `dimension`.
- **`suggestions`**: `id`, `post_id` (FK), `image_id` (FK), `raw_similarity_score`, `guard_confidence_score`, `final_score`, `rank`, `match_status`, `match_reasoning`, `is_reviewed`, `review_status`.
- **`review_decisions`**: `id`, `suggestion_id` (FK), `reviewer_id`, `action` (`APPROVE`, `REJECT`, `OVERRIDE`), `override_image_id`, `feedback_notes`.
- **`cost_logs`**: `id`, `operation_type`, `model_name`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `job_id`.
