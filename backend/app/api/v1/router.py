from fastapi import APIRouter

from app.api.v1.routes import data, health

router = APIRouter()
router.include_router(data.router, tags=["data"])
router.include_router(health.router, tags=["health"])
