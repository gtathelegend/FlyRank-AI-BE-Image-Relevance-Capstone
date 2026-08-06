from fastapi import APIRouter
from app.api.v1 import health, images, jobs, posts, reviews

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(images.router, prefix="/images", tags=["Images"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(posts.router, prefix="/posts", tags=["Posts"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])




