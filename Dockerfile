# =============================================================================
# Combined image for Coolify: builds the Vite frontend, then runs the FastAPI
# backend which serves both the API (/api/*) and the built frontend (everything
# else) on a single port. One Coolify service, one domain.
# =============================================================================

# ---------- Stage 1: build the frontend ----------
FROM node:22-slim AS frontend
WORKDIR /app/dash

# Install deps first for better layer caching
COPY dash/package.json dash/package-lock.json ./
RUN npm ci

# Build (no VITE_API_BASE -> relative /api paths, same origin as the backend)
COPY dash/ ./
RUN npm run build

# ---------- Stage 1b: build + verify the new web UI (web/), served under APP_BASE ----------
# The image only builds if web/ passes every gate (typecheck, lint, tests, i18n, budget);
# a failed build leaves Coolify running the previous version.
FROM node:24-slim@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205 AS web
WORKDIR /app/web
ARG APP_BASE=/app/
ENV APP_BASE=${APP_BASE}
COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci --ignore-scripts
COPY web/ ./
RUN npm run verify

# ---------- Stage 2: python backend + static frontends ----------
FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

WORKDIR /app

# Install python deps first for better layer caching. Every package is pinned and
# hash-checked (requirements.lock, generated from requirements.in for Python 3.12); the one
# git dependency is pinned to a commit and installed without pulling extra deps (plan B10).
# git is needed only for that install, so it is added and purged in the same layer and
# never ships in the image.
COPY backend/requirements.lock backend/requirements-git.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && pip install --no-cache-dir --require-hashes -r requirements.lock \
    && pip install --no-cache-dir --no-deps -r requirements-git.txt \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/*

# Backend code. The glob is top-level only (main.py entry + build_meta.py), so packages
# need their own COPY — the app imports zservice and radar_engine at startup, and a
# missing package takes the whole app down, not just its own routes.
COPY backend/*.py ./
COPY backend/radar_engine/ ./radar_engine/
COPY backend/zservice/ ./zservice/

# Build metadata for /api/version + server-side symbol list for /api/symbols and auto-start
# (SOURCE_COMMIT is passed by Coolify; falls back to "unknown").
ARG SOURCE_COMMIT=unknown
COPY dash/src/symbols.ts /tmp/symbols.ts
COPY dash/package.json /tmp/package.json
RUN python3 build_meta.py /tmp/symbols.ts /tmp/package.json "$SOURCE_COMMIT" /app

# Trade instruction prompts (gold analysis template) — read at runtime by main.py
COPY .claude/trade_instruction ./trade_instruction

# Built frontends (FastAPI serves FRONTEND_DIR at /): legacy dashboard at /, the new web
# UI under /app/ (APP_BASE). Removing the second line removes the new UI, nothing else.
COPY --from=frontend /app/dash/dist ./static
COPY --from=web /app/web/dist ./static/app

# Persistence is MongoDB Atlas (zservice/db) — no local DB volume needed.
ENV FRONTEND_DIR=/app/static

# Run as an unprivileged user. Code and static files stay root-owned (read-only for the
# app); the only runtime write besides temp files is the TradingView token cache, kept in
# its own directory (ZS_STATE_DIR) owned by the app user.
# Bytecode is compiled now: the app user cannot write __pycache__ into root-owned code.
RUN python -m compileall -q /app \
    && useradd --system --uid 10001 --create-home --home-dir /home/app app \
    && install -d -o app -g app -m 0700 /app/state
ENV ZS_STATE_DIR=/app/state
USER app

# Every setting and secret is configured at runtime via Coolify env vars (never baked in).
# The full list, generated from the code, is docs/config-reference.md; values are checked
# at boot, so a malformed one fails the healthcheck and the previous version keeps running.

EXPOSE 9999

# Liveness for Coolify rolling updates (python: the slim image has no curl). Two containers
# overlap during an update; the job heartbeat stops them running two auto jobs at once.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9999/api/healthz', timeout=4)"]

# --no-server-header: do not advertise uvicorn. Proxy headers are on by default; set
# FORWARDED_ALLOW_IPS (runbook) so the login rate limit sees real client IPs.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999", "--no-server-header"]
