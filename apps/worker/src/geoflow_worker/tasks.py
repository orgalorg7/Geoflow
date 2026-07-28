from geoflow_worker.celery_app import celery_app


@celery_app.task(name="geoflow.health.ping")
def ping() -> dict[str, str]:
    """Provide a lightweight task for worker and broker smoke tests."""
    return {"status": "ok", "service": "geoflow-worker"}

