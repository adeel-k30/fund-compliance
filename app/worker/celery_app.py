# Celery application configuration.
#
# Celery is a background task queue. The API sends a task message to Redis (the broker),
# and a separate Celery worker process picks it up and runs it asynchronously.
# This is why the API can return 202 immediately — the file processing happens
# out-of-band in the worker, not in the request/response cycle.
#
# `backend=redis_url` stores task results in Redis so Celery can report whether
# a task succeeded or failed (though we primarily track status in Postgres).

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "fund_compliance",
    broker=settings.redis_url,   # Redis receives task messages from the API
    backend=settings.redis_url,  # Redis stores task results/state
    include=["app.worker.tasks"] # tells Celery where to find task definitions
)

celery_app.conf.update(
    task_serializer="json",    # tasks are sent as JSON
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)