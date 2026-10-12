from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("prediction", broker=settings.celery_broker_url or settings.redis_url)
celery_app.conf.update(
    task_default_queue="prediction",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    imports=("app.tasks",),
)
