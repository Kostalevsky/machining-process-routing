from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.modules.identity.api import router as identity_router
from app.modules.runs.api import router as runs_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(identity_router, tags=["identity"])
api_router.include_router(runs_router)
