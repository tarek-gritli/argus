import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from api import api_router
from api.routes.dashboard import router as dashboard_router
from celery import Celery
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware
from shared.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.celery = Celery(broker=settings.celery_broker_url)
    yield
    await app.state.redis.aclose()


app = FastAPI(
    title="Argus Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
# CORSMiddleware must be added last (outermost) so it also attaches headers
# to early-rejection responses from AuthMiddleware/RateLimitMiddleware, not
# just successful ones — otherwise browsers report auth failures as an
# opaque CORS error instead of the real 401/429.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    return {"message": "pong"}


app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
