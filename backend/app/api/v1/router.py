from fastapi import APIRouter

from app.api.v1.routes import auth, data, health, me, onboarding, produce, recipes, reference, users

router = APIRouter()
router.include_router(auth.router, tags=["auth"])
router.include_router(data.router, tags=["data"])
router.include_router(health.router, tags=["health"])
router.include_router(me.router, tags=["me"])
router.include_router(onboarding.router, tags=["onboarding"])
router.include_router(produce.router, tags=["produce"])
router.include_router(recipes.router, tags=["recipes"])
router.include_router(reference.router, tags=["reference"])
router.include_router(users.router, tags=["users"])
