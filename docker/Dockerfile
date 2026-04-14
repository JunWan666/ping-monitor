FROM node:20-alpine AS frontend-builder

ARG NPM_REGISTRY=https://registry.npmjs.org/

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm config set registry "$NPM_REGISTRY" \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=
ARG PIP_TRUSTED_HOST=

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/app/data/ping_monitor.db \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

RUN apt-get update && apt-get install -y \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/ ./backend/

RUN if [ -n "$PIP_INDEX_URL" ]; then pip config set global.index-url "$PIP_INDEX_URL"; fi \
    && if [ -n "$PIP_EXTRA_INDEX_URL" ]; then pip config set global.extra-index-url "$PIP_EXTRA_INDEX_URL"; fi \
    && if [ -n "$PIP_TRUSTED_HOST" ]; then pip config set global.trusted-host "$PIP_TRUSTED_HOST"; fi \
    && for attempt in 1 2 3; do \
        pip install --no-cache-dir -r backend/requirements.txt && exit 0; \
        if [ "$attempt" -eq 3 ]; then exit 1; fi; \
        echo "pip install failed on attempt $attempt, retrying..." >&2; \
        sleep $((attempt * 5)); \
    done

COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "backend/main.py"]
