from celery import Celery
from worker.config import get_celery_settings
from application.models.kleandbm import Project, ProjectCreate
from services.project_service import ProjectService
import json

settings = get_celery_settings()
# print(settings)

celery = Celery(__name__)

celery.conf.update(
    broker_url=settings.broker_url,
    result_backend=settings.result_backend,
)

# new_project cannot be ProjectCreate because it cannot be serialized
@celery.task(name="create_project")
def create_project(new_project):
    result = ProjectService.create_project(ProjectCreate(**new_project))
    return result