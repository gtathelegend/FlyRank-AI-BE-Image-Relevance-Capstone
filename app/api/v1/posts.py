from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.logging import logger
from app.models.job import JobType, JobStatus
from app.models.post import PostStatus
from app.models.suggestion import MatchStatus
from app.repositories.post_repo import post_repo
from app.repositories.job_repo import job_repo
from app.repositories.embedding_repo import post_embedding_repo
from app.schemas.post import BlogPostCreate, BlogPostResponse, SinglePostCreateResponse, PostEmbeddingResponse
from app.schemas.suggestion import SuggestionResponse, MatchResultsResponse
from app.workers.post_worker import post_worker




router = APIRouter()


async def _run_post_worker_job(job_id: UUID, post_id: UUID):
    """Background task session wrapper for post embedding worker."""
    from app.main import app
    db_factory = app.dependency_overrides.get(get_db, get_db)
    async for db in db_factory():
        try:
            await post_worker.process_post_embedding_job(db, job_id, post_id)
        except Exception as e:
            logger.error(f"Background worker failed for post embedding job {job_id}: {e}")
        break



@router.post(
    "",
    response_model=SinglePostCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Blog Post",
    description="Creates a new blog post record and queues an asynchronous background task to generate text embeddings."
)
async def create_blog_post(
    post_in: BlogPostCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> SinglePostCreateResponse:
    # 1. Create BlogPost DB record
    post = await post_repo.create(
        db,
        {
            "title": post_in.title,
            "content": post_in.content,
            "author": post_in.author,
            "category": post_in.category,
            "summary": post_in.summary or post_in.content[:200],
            "tags": post_in.tags,
            "status": PostStatus.PENDING
        }
    )

    # 2. Create BatchJob for embedding generation
    job = await job_repo.create_job(
        db,
        job_type=JobType.BATCH_EMBEDDING,
        total_items=1,
        status=JobStatus.PENDING
    )

    logger.info(f"BlogPost created: id={post.id}, title='{post.title}', job_id={job.id}")

    # 3. Dispatch background task
    background_tasks.add_task(_run_post_worker_job, job.id, post.id)

    return SinglePostCreateResponse(
        message="Blog post created successfully and embedding generation queued.",
        post=BlogPostResponse.model_validate(post),
        job_id=job.id
    )


@router.get(
    "",
    response_model=List[BlogPostResponse],
    status_code=status.HTTP_200_OK,
    summary="List Blog Posts",
    description="Retrieves a paginated list of blog posts with optional status filtering."
)
async def list_blog_posts(
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(100, ge=1, le=500, description="Pagination page limit"),
    post_status: Optional[PostStatus] = Query(None, description="Filter by post status"),
    db: AsyncSession = Depends(get_db)
) -> List[BlogPostResponse]:
    posts = await post_repo.list_posts(db, skip=skip, limit=limit, status=post_status)
    return [BlogPostResponse.model_validate(p) for p in posts]


@router.get(
    "/{id}",
    response_model=BlogPostResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Blog Post Details",
    description="Retrieves full details of a blog post by UUID."
)
async def get_blog_post(
    id: UUID,
    db: AsyncSession = Depends(get_db)
) -> BlogPostResponse:
    post = await post_repo.get(db, id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BlogPost with ID '{id}' not found."
        )
    return BlogPostResponse.model_validate(post)


@router.get(
    "/{id}/embedding",
    response_model=PostEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Post Embedding Vector Metadata",
    description="Retrieves embedding metadata for a blog post."
)
async def get_post_embedding(
    id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PostEmbeddingResponse:
    post = await post_repo.get(db, id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BlogPost with ID '{id}' not found."
        )

    embedding = await post_embedding_repo.get_by_post_id(db, id)
    if not embedding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vector embedding not yet generated for post '{id}'."
        )

    return PostEmbeddingResponse.model_validate(embedding)


@router.get(
    "/{id}/matches",
    response_model=MatchResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Top Candidate Image Matches",
    description="Retrieves candidate image matches evaluated by Mismatch Guard. Prefers 'No confident match' over weak recommendations."
)
async def get_post_matches(
    id: UUID,
    top_k: int = Query(5, ge=1, le=20, description="Top K candidate limit"),
    db: AsyncSession = Depends(get_db)
) -> MatchResultsResponse:
    from app.repositories.suggestion_repo import suggestion_repo
    from app.repositories.image_repo import image_repo
    from app.services.matching_engine import matching_engine
    from app.schemas.image import ImageResponse

    post = await post_repo.get(db, id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BlogPost with ID '{id}' not found."
        )

    # Check if suggestions already exist; if not, execute matching engine
    suggestions = await suggestion_repo.get_by_post_id(db, id)
    if not suggestions:
        try:
            suggestions = await matching_engine.generate_matches_for_post(db, id, top_k=top_k)
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )

    confident_matches = [s for s in suggestions if s.match_status == MatchStatus.MATCHED]
    has_confident_match = len(confident_matches) > 0

    if has_confident_match:
        status_msg = f"Found {len(confident_matches)} confident candidate image matches."
    else:
        status_msg = "No confident match found. Rejected all candidates due to low similarity or semantic conflict."

    response_matches: List[SuggestionResponse] = []
    for sug in suggestions[:top_k]:
        img = await image_repo.get(db, sug.image_id)
        img_resp = ImageResponse.model_validate(img) if img else None

        response_matches.append(
            SuggestionResponse(
                id=sug.id,
                post_id=sug.post_id,
                image_id=sug.image_id,
                image=img_resp,
                similarity_score=sug.final_score,
                raw_similarity_score=sug.raw_similarity_score,
                guard_confidence_score=sug.guard_confidence_score,
                rank=sug.rank,
                match_status=sug.match_status,
                match_reasoning=sug.match_reasoning,
                is_reviewed=sug.is_reviewed,
                created_at=sug.created_at
            )
        )

    return MatchResultsResponse(
        post_id=id,
        has_confident_match=has_confident_match,
        status_message=status_msg,
        total_candidates_evaluated=len(suggestions),
        matches=response_matches
    )


@router.post(
    "/{id}/match",
    response_model=MatchResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Semantic Matching Pipeline",
    description="Forces re-evaluation of Mismatch Guard and semantic matching pipeline."
)
async def trigger_post_matching(
    id: UUID,
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
) -> MatchResultsResponse:
    from app.services.matching_engine import matching_engine
    from app.repositories.image_repo import image_repo
    from app.schemas.image import ImageResponse

    try:
        suggestions = await matching_engine.generate_matches_for_post(db, id, top_k=top_k)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )

    confident_matches = [s for s in suggestions if s.match_status == MatchStatus.MATCHED]
    has_confident_match = len(confident_matches) > 0

    if has_confident_match:
        status_msg = f"Found {len(confident_matches)} confident candidate image matches."
    else:
        status_msg = "No confident match found. Rejected all candidates due to low similarity or semantic conflict."

    response_matches: List[SuggestionResponse] = []
    for sug in suggestions[:top_k]:
        img = await image_repo.get(db, sug.image_id)
        img_resp = ImageResponse.model_validate(img) if img else None

        response_matches.append(
            SuggestionResponse(
                id=sug.id,
                post_id=sug.post_id,
                image_id=sug.image_id,
                image=img_resp,
                similarity_score=sug.final_score,
                raw_similarity_score=sug.raw_similarity_score,
                guard_confidence_score=sug.guard_confidence_score,
                rank=sug.rank,
                match_status=sug.match_status,
                match_reasoning=sug.match_reasoning,
                is_reviewed=sug.is_reviewed,
                created_at=sug.created_at
            )
        )

    return MatchResultsResponse(
        post_id=id,
        has_confident_match=has_confident_match,
        status_message=status_msg,
        total_candidates_evaluated=len(suggestions),
        matches=response_matches
    )


