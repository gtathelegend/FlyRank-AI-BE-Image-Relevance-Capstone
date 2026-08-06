from fastapi import APIRouter
from app.api.v1 import health, images

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(images.router, prefix="/images", tags=["Images"])

