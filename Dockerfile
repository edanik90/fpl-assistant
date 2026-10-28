# Immutable multi-architecture image digests; update deliberately.
FROM node:25-bookworm-slim@sha256:81db02c4b671288a03915da9534dbd54f96d0e7c24d80ccc54f5b36b2e684370 AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-trixie@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONPATH=/opt/python
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --target /opt/python -r requirements.txt \
    && mkdir /runtime-data && chown 10001:10001 /runtime-data
COPY backend/app ./app
COPY backend/alembic ./alembic

FROM backend AS test
COPY backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY backend/tests ./tests
CMD ["python", "-m", "pytest", "-q", "tests"]

FROM backend AS runtime-files
COPY scripts/prepare-runtime.py /tmp/prepare-runtime.py
RUN python /tmp/prepare-runtime.py

FROM gcr.io/distroless/cc-debian13:nonroot@sha256:3ee00291cf386ec52a552e6a858d555debd74776eb4bfa53fa3df2cd6677515e AS runtime
WORKDIR /app
# Carry the official patched CPython and only required native libraries, with
# their package metadata. Never purge essentials from a general-purpose Debian OS.
COPY --from=runtime-files /runtime-root/ /
COPY --from=backend /opt/python /opt/python
COPY --from=backend /app/app ./app
COPY --from=backend /app/alembic ./alembic
COPY --from=backend --chown=10001:10001 /runtime-data/ /data/
COPY --from=frontend /web/dist ./static
ENV DATA_DIR=/data STATIC_DIR=/app/static PYTHONPATH=/opt/python PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LD_LIBRARY_PATH=/opt/runtime-libs:/usr/local/lib
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]
ENTRYPOINT ["/usr/bin/python3"]
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
