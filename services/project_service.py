import json
from confluent_kafka import Producer

from application.models.kleandbm import ProjectHeader, ProjectCreate, PromptGenerator
from application.config import get_settings
import services.utils as services_utils
from typing import List

class ProjectService:
    settings = get_settings()
    producer = Producer({'bootstrap.servers':settings.kafka_server})

    ## The kafka methods are here and not in utils so that the producer is here and remains open for performance reasons
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
        project_id = new_project.id
        ProjectService.kafka_produce('project-updates', project_id, new_project.model_dump_json())
        system_message = PromptGenerator.get_create_project_sytem_prompt(new_project)
        user_message = PromptGenerator.get_create_project_user_prompt(new_project)
        raw_data_model = json.loads(services_utils.prompt_openai(ProjectService.settings.openai_model, system_message, user_message))
        # @TODO: This should be of Project data Type
        # @TODO: Determine if it's best to move Save to the Project datatype
        suggested_data_model = services_utils.complete_project(project_id, raw_data_model)
        nodes = services_utils.generate_nodes(suggested_data_model, project_id)

        for table in suggested_data_model['tables']:
            ProjectService.kafka_produce('table-updates', project_id, json.dumps(table)) # Saving tables

        for relationship in suggested_data_model['relationships']:
            ProjectService.kafka_produce('relationship-updates', project_id, json.dumps(relationship)) # Saving relationsihps

        for node in nodes:
            ProjectService.kafka_produce('node-updates', project_id, json.dumps(node)) # Saving node

        return suggested_data_model
    
    @staticmethod
    async def get_projects() -> List[ProjectHeader]:
        query = "SELECT * FROM PROJECTS WHERE `active`=true;" 
        ksql_response = await services_utils.query_ksql(ProjectService.settings.ksqldb_cluster, query)
        projects_json = services_utils.process_ksql_response(ksql_response)
        response_list = [ProjectHeader(**p) for p in json.loads(json.dumps(projects_json))]
        return response_list