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
    mongodb_backend_settings={
        'database': settings.result_db,
        'taskmeta_collection': settings.result_collection
    }
)

# new_project cannot be ProjectCreate because it cannot be serialized
@celery.task(name="create_project")
def create_project(new_project, user_payload):
    print (user_payload)
    result = ProjectService.create_project(ProjectCreate(**new_project), user_payload)
    return result

@celery.task(name="generate_table_recommendations")
def generate_table_recommendations(project_id, prompt, position):
    result = ProjectService.generate_ai_table_recommendations(project_id, prompt, position)
    return result

@celery.task(name="generate_table_edits")
def generate_table_edits(project_id, user_request):
    result = ProjectService.generate_ai_table_edits(project_id, user_request)
    return result

@celery.task(name="update_naming_rules")
def update_naming_rules(project_id, user_request):
    result = ProjectService.update_naming_rules(project_id, user_request)
    return result