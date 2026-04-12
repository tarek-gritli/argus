from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from api import api_router
from celery import Celery
from fastapi import FastAPI
from shared.config import get_settings

settings = get_settings()


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


@app.get("/ping")
async def ping():
    return {"message": "pong"}


app.include_router(api_router, prefix=settings.api_prefix)
