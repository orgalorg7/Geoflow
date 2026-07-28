from celery import Celery
from geoflow_config import get_settings

settings = get_settings()

celery_app = Celery(
    "geoflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["geoflow_worker.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    broker_connection_retry_on_startup=True,
)

