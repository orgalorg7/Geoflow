FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY packages/config/python /workspace/packages/config/python
COPY apps/api /workspace/apps/api

RUN pip install -e /workspace/packages/config/python -e "/workspace/apps/api[dev]"

WORKDIR /workspace/apps/api

EXPOSE 8000

CMD ["uvicorn", "geoflow_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
