import json
from confluent_kafka import Producer

from application.models.kleandbm import Project, ProjectCreate
from application.config import get_settings
import services.utils as services_utils
from typing import List

class ProjectService:
    settings = get_settings()
    producer = Producer({'bootstrap.servers':settings.kafka_server})

    @staticmethod
    def kafka_produce(topic, key, value):
        # Due to this celeri/kafka-python issue the producer has to be local when called from a celeri worker
        # https://github.com/dpkp/kafka-python/issues/1098
        producer = Producer({'bootstrap.servers':ProjectService.settings.kafka_server})
        producer.produce(topic, key=key, value=value)
        producer.flush()

    @staticmethod
    async def async_kafka_produce(topic, key, value):
        ProjectService.producer.produce(topic, key=key, value=value)
        ProjectService.producer.flush()

    # TODO: Change the return type to Project and handle that in Celeri
    @staticmethod
    def create_project(new_project: ProjectCreate):
        ProjectService.kafka_produce('project-updates', new_project.id, new_project.model_dump_json())
        return ({'result': 'success'})    
    
    @staticmethod
    async def get_projects() -> List[Project]:
        query = "SELECT * FROM PROJECTS WHERE `active`=true;" 
        ksql_response = await services_utils.query_ksql(ProjectService.settings.ksqldb_cluster, query)
        projects_json = services_utils.process_ksql_response(ksql_response)
        response_list = [Project(**p) for p in json.loads(json.dumps(projects_json))]
        return response_list