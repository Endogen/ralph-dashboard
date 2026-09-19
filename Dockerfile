FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM node:22-bookworm-slim AS agent-cli
# Explicit versions keep deployments reproducible. Update alongside runner tests.
ARG CODEX_VERSION=0.155.1
ARG CLAUDE_VERSION=2.1.278
RUN npm install -g @openai/codex@${CODEX_VERSION} @anthropic-ai/claude-code@${CLAUDE_VERSION}

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git curl ripgrep \
    && rm -rf /var/lib/apt/lists/*
COPY --from=agent-cli /usr/local /opt/node
ENV PATH="/opt/node/bin:${PATH}"
ARG RALPH_UID=1000
ARG RALPH_GID=1000
RUN groupadd -g ${RALPH_GID} ralph && useradd -m -u ${RALPH_UID} -g ralph ralph \
    && mkdir /data /projects && chown ralph:ralph /data /projects
WORKDIR /app
COPY backend/ ./backend/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir ./backend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
ENV RALPH_FRONTEND_DIST=/app/frontend/dist \
    RALPH_CREDENTIALS_FILE=/data/credentials.yaml \
    RALPH_DATABASE_PATH=/data/dashboard.db \
    RALPH_PROJECT_DIRS=/projects
USER ralph
EXPOSE 8420
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8420"]
