# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN --mount=type=secret,id=ca_bundle \
    if [ -f /run/secrets/ca_bundle ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca_bundle; fi; npm ci
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock backend/requirements.lock
RUN --mount=type=secret,id=ca_bundle \
    if [ -f /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; pip install --no-cache-dir -r backend/requirements.lock
COPY --chown=10001:10001 backend/ backend/
COPY --from=frontend --chown=10001:10001 /build/dist frontend/dist
RUN useradd --uid 10001 --create-home parser && mkdir -p data && chown parser:parser data
USER parser
EXPOSE 8000
CMD ["uvicorn","backend.app.api:app","--host","0.0.0.0","--port","8000","--no-access-log"]
