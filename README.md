# AI Image Understanding & Content Matching Engine

A production-grade backend engine engineered with **FastAPI**, **PostgreSQL + pgvector**, **Google Gemini 1.5 Flash Vision AI**, **Google Text Embedding 004**, and an automated multi-tier **Mismatch Guard**. Designed to automatically analyze catalog image visual assets, extract structured AI metadata, generate multimodal 768-dimensional vector embeddings, match blog posts to relevant images, prevent misleading recommendations via species & biome guardrails, enable human-in-the-loop (HITL) review workflows, quantify precision via benchmark evaluations, and track operational costs in real time.

---

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Technology Stack](#technology-stack)
- [AI Pipeline & System Architecture](#ai-pipeline--system-architecture)
  - [Vision Processing Pipeline](#vision-processing-pipeline)
  - [Embedding Pipeline](#embedding-pipeline)
  - [Semantic Relevance Engine](#semantic-relevance-engine)
  - [Mismatch Guard Guardrail System](#mismatch-guard-guardrail-system)
  - [Human Review Workflow](#human-review-workflow)
  - [Quantitative Evaluation Engine](#quantitative-evaluation-engine)
  - [Cost Tracking & Analytics Dashboard](#cost-tracking--analytics-dashboard)
- [Installation & Setup](#installation--setup)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Future Improvements](#future-improvements)

---

## Project Overview
Publishing platforms and content management systems frequently suffer from poor image relevance—blog posts are often paired with generic, misleading, or visually conflicting stock photos. Standard text search or visual feature similarity alone is insufficient because it lacks semantic guardrails (for example, pairing a red fox post with a timber wolf image due to similar forest backgrounds).

This engine solves content relevance by combining:
1. **Multimodal AI Vision Extraction** (captions, scene descriptions, tags, subjects, species, biomes).
2. **Dense Vector Embeddings** (768-dimensional `text-embedding-004` representations).
3. **Multi-Tiered Mismatch Guard** (species & environment conflict checks, cosine similarity thresholds).
4. **Human-in-the-Loop Review System** (auditing, approval/rejection, feedback notes).
5. **Evaluation Engine & Financial Analytics** (Precision@K metrics, token accounting, USD cost tracking).

---

## Architecture

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

## Folder Structure

```text
FlyRank-AI-BE-Image-Relevance-Capstone/
├── alembic/                      # Database schema migration scripts (001 to 007)
│   └── versions/
├── app/
│   ├── api/                      # API router and endpoints
│   │   ├── deps.py
│   │   ├── router.py
│   │   └── v1/                   # Endpoint versions
│   │       ├── health.py         # System health & DB connection status
│   │       ├── images.py         # Image ingestion & metadata API
│   │       ├── jobs.py           # Background batch job tracking API
│   │       ├── posts.py          # Blog post creation & matching API
│   │       ├── reviews.py        # Human review workflow API
│   │       ├── evaluation.py     # Quality evaluation engine API
│   │       └── metrics.py        # Analytics & cost tracking API
│   ├── core/                     # Application configuration & database setup
│   │   ├── config.py             # Pydantic BaseSettings environment config
│   │   ├── database.py           # SQLAlchemy AsyncEngine & Session maker
│   │   └── logging.py            # Loguru structured logging configuration
│   ├── models/                   # SQLAlchemy ORM Data Models
│   │   ├── base.py
│   │   ├── cost.py               # CostLog model & OperationType enum
│   │   ├── embedding.py          # ImageEmbedding & PostEmbedding models
│   │   ├── image.py              # Image catalog model & ImageStatus enum
│   │   ├── job.py                # BatchJob model & JobStatus/JobType enums
│   │   ├── metadata.py           # ImageMetadata vision extraction model
│   │   ├── post.py               # BlogPost model & PostStatus enum
│   │   ├── review.py             # ReviewDecision model & ReviewAction enum
│   │   └── suggestion.py         # Suggestion model & MatchStatus/ReviewStatus
│   ├── repositories/             # Data access repository layer
│   │   ├── base.py
│   │   ├── embedding_repo.py
│   │   ├── image_repo.py
│   │   ├── job_repo.py
│   │   ├── metadata_repo.py
│   │   ├── post_repo.py
│   │   ├── review_repo.py
│   │   └── suggestion_repo.py
│   ├── schemas/                  # Pydantic validation & response schemas
│   │   ├── analytics.py
│   │   ├── evaluation.py
│   │   ├── health.py
│   │   ├── image.py
│   │   ├── post.py
│   │   ├── review.py
│   │   ├── suggestion.py
│   │   └── vision.py
│   ├── services/                 # Core AI business logic services
│   │   ├── analytics_service.py  # System metrics & financial accounting
│   │   ├── cost_tracker.py       # AI token pricing & cost logging engine
│   │   ├── embedding_pipeline.py # 768-dim vector embedding generation
│   │   ├── evaluation_engine.py  # Precision@K & benchmark evaluator
│   │   ├── matching_engine.py    # Cosine vector similarity search engine
│   │   ├── mismatch_guard.py     # Multi-tier species & environment guardrails
│   │   ├── storage_service.py    # Image upload, SHA-256 deduplication, disk storage
│   │   └── vision_pipeline.py    # Gemini Flash Vision AI structured analyzer
│   ├── utils/                    # Vector math utilities
│   │   └── vector_math.py
│   └── workers/                  # Async background worker tasks
│       ├── post_worker.py        # Post embedding worker
│       └── vision_worker.py      # Vision processing & metadata worker
├── storage/                      # Persistent storage directory
│   ├── datasets/                 # Evaluation dataset (eval_dataset.json)
│   ├── embeddings/               # Local vector cache storage
│   ├── images/                   # Uploaded image assets storage
│   └── metadata/                 # Cached metadata JSON
├── tests/                        # Automated unit & integration test suite
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_health.py
│   ├── test_stage1_images.py
│   ├── test_stage2_vision.py
│   ├── test_stage3_embeddings.py
│   ├── test_stage4_matching.py
│   ├── test_stage5_mismatch_guard.py
│   ├── test_stage6_reviews.py
│   ├── test_stage7_evaluation.py
│   ├── test_stage8_analytics.py
│   └── test_stage9_e2e.py
├── .env.example                  # Environment configuration template
├── BUILDLOG.md                   # Development history & build log
├── capstone.yaml                 # Project manifest file
├── DESIGN.md                     # Technical design document
├── docker-compose.yml            # Multi-container Docker compose configuration
├── Dockerfile                    # Containerization instructions
├── EVIDENCE.md                   # System verification & execution evidence
├── requirements.txt              # Python dependency requirements
└── README.md                     # Project documentation
```

---

## Technology Stack
- **Language**: Python 3.12+
- **API Framework**: FastAPI & Pydantic v2
- **Database**: PostgreSQL 16 with `pgvector` vector extension
- **ORM & Driver**: SQLAlchemy 2.0 (AsyncIO) & `asyncpg`
- **Database Migrations**: Alembic
- **AI Computer Vision**: Google Gemini 1.5 Flash Vision AI
- **AI Embeddings**: Google Text Embedding 004 (`768`-dimensional dense vectors)
- **Image Processing**: Pillow (PIL)
- **Containerization**: Docker & Docker Compose
- **Test Runner**: Pytest & Pytest-AsyncIO

---

## AI Pipeline & System Architecture

### Vision Processing Pipeline
1. Images uploaded via API are saved to disk with SHA-256 deduplication.
2. Background workers invoke the **Vision Pipeline Service** using Gemini 1.5 Flash Vision AI.
3. Strict system prompts enforce deterministic raw JSON extraction without markdown blocks.
4. Outputs are validated using Pydantic (`StructuredVisionResponse`), extracting `primary_subject`, `secondary_subjects`, `caption`, `scene_description`, `tags`, `objects`, `animals`, `colors`, `environment`, `ocr_text`, and `confidence`.

### Embedding Pipeline
1. Constructs rich metadata descriptions combining visual attributes, captions, subjects, biomes, and tags.
2. Invokes Google `text-embedding-004` to generate normalized 768-dimensional float vectors.
3. For blog posts, generates weighted chunk embeddings (title, summary, body content) and blends them into a unified post embedding.

### Semantic Relevance Engine
1. Retrieves top candidate image vector embeddings for a given blog post.
2. Computes normalized cosine similarity scores between the post vector and image vectors.
3. Ranks candidates by similarity score.

### Mismatch Guard Guardrail System
Prevents misleading or contextually invalid recommendations using a 4-tier evaluation pipeline:
- **Tier 1 (Similarity Threshold)**: Rejects candidates with raw similarity `< 0.70`.
- **Tier 2 (Species Conflict)**: Detects species incompatibilities between post content and image metadata (e.g. Fox vs Wolf, Dog vs Wolf, Cat vs Lion).
- **Tier 3 (Biome/Environment Conflict)**: Detects biome incompatibilities (e.g. Forest vs City skyscraper, Ocean vs Desert dunes).
- **Tier 4 (LLM Verification)**: Optional secondary LLM verification for live production keys.
- **Preference for "No confident match"**: If top candidates fail guard rules, the system returns `has_confident_match = False` rather than serving weak or misleading recommendations.

### Human Review Workflow
- Exposes human review management endpoints (`/api/v1/reviews`).
- Reviewers can view nested details (Image, Blog Post, similarity score, caption, tags, recommendation reason, Mismatch Guard result).
- Supports approving (`POST /reviews/{id}/approve`) or rejecting (`POST /reviews/{id}/reject`) candidates with reviewer IDs and feedback notes.
- Maintains a persistent audit trail in `review_decisions`.

### Quantitative Evaluation Engine
- Benchmarks system precision against a curated ground-truth evaluation dataset (`storage/datasets/eval_dataset.json`).
- Calculates: `Precision@1`, `Precision@3`, `Precision@5`, `Acceptance Rate`, `Rejection Rate`, `Average Similarity`, `Average Confidence`, `Mismatch Guard Trigger Rate`, and Confusion Matrix (`Accuracy`, `Precision`, `Recall`, `F1 Score`).

### Cost Tracking & Analytics Dashboard
- Automatically records API token consumption (`input_tokens`, `output_tokens`) and calculates estimated USD costs per operation type.
- Exposes metrics endpoints:
  - `GET /api/v1/metrics`: System overview dashboard.
  - `GET /api/v1/metrics/cost`: Financial cost and token breakdown.
  - `GET /api/v1/metrics/jobs`: Job execution performance statistics.

---

## Installation & Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 16+ with `pgvector` extension (or Docker)

### 1. Clone Repository & Environment Setup
```bash
git clone https://github.com/gtathelegend/FlyRank-AI-BE-Image-Relevance-Capstone.git
cd FlyRank-AI-BE-Image-Relevance-Capstone

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and fill in your Gemini API key:
```bash
cp .env.example .env
```

### 3. Database Migration
Run Alembic migrations to create PostgreSQL tables and vector indexes:
```bash
alembic upgrade head
```

### 4. Run Application Server
```bash
uvicorn app.main:app --reload --port 8000
```
The API documentation will be available at `http://localhost:8000/docs`.

---

## Docker Deployment

Deploy the entire stack (PostgreSQL + pgvector + FastAPI engine) with a single command:

```bash
docker-compose up --build -d
```

Access services at:
- **API Server**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/docs`

To stop containers:
```bash
docker-compose down
```

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PROJECT_NAME` | Name of the application | `"AI Image Understanding & Content Matching Engine"` |
| `ENVIRONMENT` | Deployment stage | `"development"` |
| `API_V1_STR` | API prefix string | `"/api/v1"` |
| `POSTGRES_SERVER` | Database server host | `"localhost"` |
| `POSTGRES_PORT` | Database server port | `5432` |
| `POSTGRES_USER` | Database username | `"postgres"` |
| `POSTGRES_PASSWORD` | Database password | `"postgres"` |
| `POSTGRES_DB` | Database name | `"image_matching_db"` |
| `DATABASE_URL` | Async SQLAlchemy connection URL | `"postgresql+asyncpg://..."` |
| `GEMINI_API_KEY` | Google Gemini API Key | `""` |
| `MISMATCH_GUARD_MIN_SIMILARITY` | Minimum similarity threshold | `0.70` |
| `MISMATCH_GUARD_MIN_CONFIDENCE` | Minimum guard confidence | `0.80` |

---

## API Documentation

Key endpoints exposed under `/api/v1`:

### Ingestion & Jobs
- `POST /api/v1/images/upload`: Upload a single image file.
- `POST /api/v1/images/batch`: Upload multiple image files in batch.
- `GET /api/v1/images`: List uploaded catalog images.
- `GET /api/v1/images/{id}`: Get single image details.
- `GET /api/v1/images/{id}/metadata`: Get extracted AI vision metadata.
- `GET /api/v1/jobs/{id}`: Check background processing job status.
- `POST /api/v1/jobs/{id}/process`: Trigger vision processing worker.

### Blog Posts & Matching
- `POST /api/v1/posts`: Create a new blog post and queue vector embedding generation.
- `GET /api/v1/posts`: List blog posts.
- `GET /api/v1/posts/{id}/matches`: Get candidate image recommendations evaluated by Mismatch Guard.
- `POST /api/v1/posts/{id}/match`: Re-trigger matching pipeline for a blog post.

### Human Review Workflow
- `GET /api/v1/reviews`: Query review candidates with filters (`status`, `image_id`, `post_id`, `date`).
- `GET /api/v1/reviews/{id}`: Inspect detailed review item.
- `POST /api/v1/reviews/{id}/approve`: Approve recommendation with optional notes.
- `POST /api/v1/reviews/{id}/reject`: Reject recommendation with optional notes.

### Evaluation & Metrics Analytics
- `GET /api/v1/evaluation`: Full quantitative evaluation report.
- `GET /api/v1/evaluation/metrics`: Direct metric calculation summary.
- `GET /api/v1/metrics`: Overall system analytics dashboard metrics.
- `GET /api/v1/metrics/cost`: Financial cost and token usage breakdown.
- `GET /api/v1/metrics/jobs`: Background job performance analytics.

---

## Testing

Run all 31 automated unit, integration, failure mode, and E2E test suites:

```bash
python -m pytest
```

Expected output:
```text
======================= 31 passed, 6 warnings in 19.14s =======================
```

---

## Future Improvements
1. **HNSW Vector Indexing**: Upgrade pgvector IVFFlat index to HNSW index for sub-millisecond retrieval across millions of catalog images.
2. **Multi-Region Storage Backup**: Integrate S3/GCS blob storage for multi-region media replication.
3. **Webhooks & Event Dispatches**: Emit webhook notifications when human review decisions are finalized.
