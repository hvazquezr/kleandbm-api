from celery import Celery
from worker.config import get_celery_settings
from application.models.kleandbm import ProjectCreate
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

@celery.task(name="get_sql")
def get_project_sql(project_id):
    result = ProjectService.get_project_sql(project_id)
    return result

@celery.task(name="generate_table_recommendations")
def generate_table_recommendations(project_id, prompt):
    result = ProjectService.generate_ai_table_recommendations(project_id, prompt)
    return result

@celery.task(name="generate_table_edits")
def generate_table_edits(project_id, user_request):
    result = ProjectService.generate_ai_table_edits(project_id, user_request)
    return result