# syntax=docker/dockerfile:1.7

############################################
# Builder (to cache wheels if you expand later)
############################################
FROM python:3.11-slim AS builder

WORKDIR /wheels
ENV PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

############################################
# Runtime
############################################
FROM python:3.11-slim

# Optional: install curl for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

# Security best practices
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user
ARG APP_USER=appuser
ARG APP_UID=10001
ARG APP_GID=10001
ARG APP_VERSION=dev
RUN groupadd -g ${APP_GID} ${APP_USER} \
  && useradd -u ${APP_UID} -g ${APP_GID} -m -s /usr/sbin/nologin ${APP_USER}

WORKDIR /app

# Install deps from wheels (fast, offline-friendly)
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Copy app
COPY unlock_schedule /app/unlock_schedule

# Burn version into the image (can be overridden at runtime).
ENV UNLOCK_SCHEDULE_VERSION=${APP_VERSION}

# App defaults (you can override in compose/env)
ENV GCAL_SERVICE_ACCOUNT_JSON=/secrets/service-account.json

EXPOSE 8000

# Basic healthcheck on the root page
HEALTHCHECK --interval=30s --timeout=3s --retries=5 \
  CMD curl -fsS http://localhost:8000/health || exit 1

USER ${APP_USER}

# Uvicorn server
CMD ["uvicorn", "unlock_schedule.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
