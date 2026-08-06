from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.logging import logger
from app.models.job import JobType, JobStatus
from app.models.post import PostStatus
from app.repositories.post_repo import post_repo
from app.repositories.job_repo import job_repo
from app.repositories.embedding_repo import post_embedding_repo
from app.schemas.post import BlogPostCreate, BlogPostResponse, SinglePostCreateResponse, PostEmbeddingResponse
from app.workers.post_worker import post_worker

router = APIRouter()


async def _run_post_worker_job(job_id: UUID, post_id: UUID):
    """Background task session wrapper for post embedding worker."""
    async for db in get_db():
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
