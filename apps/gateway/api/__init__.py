from fastapi import APIRouter

from .routes import webhooks
from .routes.admin import router as admin_router
from .routes.auth import router as auth_router
from .routes.integrations import router as integrations_router
from .routes.oauth import router as oauth_router
from .routes.reviews import router as reviews_router

api_router = APIRouter()

api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(integrations_router, tags=["integrations"])
api_router.include_router(oauth_router, prefix="/oauth", tags=["oauth"])
