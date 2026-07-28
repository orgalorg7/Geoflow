FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY packages/config/python /workspace/packages/config/python
COPY apps/worker /workspace/apps/worker

RUN pip install -e /workspace/packages/config/python -e "/workspace/apps/worker[dev]"

WORKDIR /workspace/apps/worker

CMD ["celery", "--app", "geoflow_worker.celery_app:celery_app", "worker", "--loglevel=INFO"]
