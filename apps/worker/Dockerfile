FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY packages/config/python /workspace/packages/config/python
COPY packages/geospatial-core /workspace/packages/geospatial-core
COPY apps/worker /workspace/apps/worker

RUN pip install \
    -e /workspace/packages/config/python \
    -e /workspace/packages/geospatial-core \
    -e "/workspace/apps/worker[dev]"

WORKDIR /workspace/apps/worker

CMD ["celery", "--app", "geoflow_worker.celery_app:celery_app", "worker", "--loglevel=INFO"]
