from celery import Celery
from worker.config import get_celery_settings

settings = get_celery_settings()
# print(settings)

celery = Celery(__name__)

celery.conf.update(
    broker_url=settings.broker_url,
    result_backend=settings.result_backend,
)

@celery.task(name="create_task")
def create_task():
    # Simulate a long-running task
    import time
    time.sleep(10)
    return "Task completed!"

