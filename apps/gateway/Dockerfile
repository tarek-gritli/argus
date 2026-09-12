# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv==0.8.23
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --package gateway

FROM python:3.12-slim

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8080

# Cloud Run injects $PORT (defaults to 8080); Settings/secrets come from env vars, never baked in.
CMD ["sh", "-c", "uvicorn gateway_main:app --host 0.0.0.0 --port ${PORT:-8080}"]
