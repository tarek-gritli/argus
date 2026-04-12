from fastapi import APIRouter

from .routes import webhooks

api_router = APIRouter()

api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
