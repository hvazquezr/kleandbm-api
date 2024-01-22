import json
import os
from fastapi.responses import FileResponse
from confluent_kafka import Producer
from application.models.PromptGenerator import PromptGenerator
from application.models.kleandbm import Project, ProjectHeader, ProjectCreate, ProjectUpdate, NodeUpdate, TableUpdate, RelationshipUpdate, SQLResponse
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
        system_message = PromptGenerator.get_create_project_sytem_prompt(new_project)
        user_message = PromptGenerator.get_create_project_user_prompt(new_project)
        raw_data_model = json.loads(services_utils.prompt_openai(ProjectService.settings.openai_model, system_message, user_message))
        # @TODO: This should be of Project data Type
        # @TODO: Determine if it's best to move Save to the Project datatype
        suggested_data_model = services_utils.complete_project(project_id, raw_data_model)
        nodes = services_utils.generate_nodes(suggested_data_model, project_id)
        
        new_project.description = suggested_data_model['description']
        ProjectService.kafka_produce('project-updates', project_id, new_project.model_dump_json(exclude_none=True))
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
        projects_json = await services_utils.async_query_ksql(ProjectService.settings.ksqldb_cluster, query)
        response_list = [ProjectHeader(**p) for p in projects_json]
        return response_list
    
    @staticmethod
    async def async_get_project(id) -> Project:
        result = None
        project_query = "SELECT * FROM PROJECTS WHERE `active`=true and `id`=\'" + id + "\';"
        project_dict = (await services_utils.async_query_ksql(ProjectService.settings.ksqldb_cluster, project_query))
        if len(project_dict) >= 1: #should be no more than 1
            tables_query = "SELECT * FROM TABLES WHERE `active`=true and `projectId`=\'" + id + "\';"
            relationships_query = "SELECT * FROM RELATIONSHIPS WHERE `active`=true and `projectId`=\'" + id + "\';"
            nodes_query = "SELECT * FROM NODES WHERE `active`=true and `projectId`=\'" + id + "\';"
            tables = await services_utils.async_query_ksql(ProjectService.settings.ksqldb_cluster, tables_query)
            relationships = await services_utils.async_query_ksql(ProjectService.settings.ksqldb_cluster, relationships_query)
            nodes = await services_utils.async_query_ksql(ProjectService.settings.ksqldb_cluster, nodes_query)
            project_dict[0]['tables'] = tables
            project_dict[0]['relationships'] = relationships
            project_dict[0]['nodes'] = nodes
            result = Project(**(project_dict[0]))
        return result
    
    @staticmethod
    def get_project(id) -> Project:
        result = None
        project_query = "SELECT * FROM PROJECTS WHERE `active`=true and `id`=\'" + id + "\';"
        project_dict = services_utils.query_ksql(ProjectService.settings.ksqldb_cluster, project_query)
        if len(project_dict) >= 1: #should be no more than 1
            tables_query = "SELECT * FROM TABLES WHERE `active`=true and `projectId`=\'" + id + "\';"
            relationships_query = "SELECT * FROM RELATIONSHIPS WHERE `active`=true and `projectId`=\'" + id + "\';"
            nodes_query = "SELECT * FROM NODES WHERE `active`=true and `projectId`=\'" + id + "\';"
            tables = services_utils.query_ksql(ProjectService.settings.ksqldb_cluster, tables_query)
            relationships = services_utils.query_ksql(ProjectService.settings.ksqldb_cluster, relationships_query)
            nodes = services_utils.query_ksql(ProjectService.settings.ksqldb_cluster, nodes_query)
            project_dict[0]['tables'] = tables
            project_dict[0]['relationships'] = relationships
            project_dict[0]['nodes'] = nodes
            result = Project(**(project_dict[0]))
        return result

    @staticmethod
    async def update_project(id, updated_project) -> ProjectUpdate:
        updated_project.id = id
        await ProjectService.async_kafka_produce('project-updates', id, updated_project.model_dump_json(exclude_none=True))
        return updated_project
    
    @staticmethod
    async def delete_project(id):
        to_delete_project = ProjectUpdate(id = id, active=False)
        await ProjectService.async_kafka_produce('project-updates', id, to_delete_project.model_dump_json(exclude_none=True))

    @staticmethod
    async def update_node(project_id, node_id, updated_node) -> NodeUpdate:
        updated_node.id = node_id
        await ProjectService.async_kafka_produce('node-updates', project_id, updated_node.model_dump_json(exclude_none=True))
        await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified
        return updated_node

    @staticmethod
    async def delete_node(project_id, node_id):
        to_delete_node = NodeUpdate(id = node_id, active=False)
        await ProjectService.async_kafka_produce('node-updates', project_id, to_delete_node.model_dump_json(exclude_none=True))
        await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified

    @staticmethod
    async def update_table(project_id, table_id, updated_table) -> TableUpdate:
        updated_table.id = table_id
        await ProjectService.async_kafka_produce('table-updates', project_id, updated_table.model_dump_json(exclude_none=True))
        await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified
        return updated_table

    @staticmethod
    async def delete_table(project_id, table_id):
        to_delete_table = TableUpdate(id = table_id, active=False)
        await ProjectService.async_kafka_produce('table-updates', project_id, to_delete_table.model_dump_json(exclude_none=True))
        await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified

    @staticmethod
    async def update_relationship(project_id, relationship_id, updated_relationship) -> RelationshipUpdate:
        updated_relationship.projectId = project_id
        updated_relationship.id = relationship_id
        await ProjectService.async_kafka_produce('relationship-updates', project_id, updated_relationship.model_dump_json(exclude_none=True))
        await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified
        return updated_relationship

    @staticmethod
    async def delete_relationship(project_id, relationship_id):
        to_delete_relationship = RelationshipUpdate(id = relationship_id, active=False)
        await ProjectService.async_kafka_produce('relationship-updates', project_id, to_delete_relationship.model_dump_json(exclude_none=True))
        await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified

    # Cannot be async because it will be used as Celeri
    @staticmethod
    def get_project_sql(id):
        project = ProjectService.get_project(id)
        del project.nodes
        system_message = PromptGenerator.get_sql_system_prompt(project)
        user_message = PromptGenerator.get_sql_user_prompt(project)
        sql = services_utils.prompt_openai(ProjectService.settings.openai_model, system_message, user_message, response_type=services_utils.ResponseType.SQL)
        return SQLResponse(sql=sql).model_dump()
    
    # Cannot be async because it will be used as Celeri
    @staticmethod
    def generate_ai_table_recommendations(id, prompt, position):
        project = ProjectService.get_project(id)
        response = {}
        system_message = PromptGenerator.get_ai_add_table_system_prompt(project)
        user_message = PromptGenerator.get_ai_add_table_user_prompt(project, prompt)
        response['tables'] = json.loads(services_utils.prompt_openai(ProjectService.settings.openai_model, system_message, user_message))
        response = services_utils.complete_project(id, response)
        response = services_utils.complete_response_for_ai_tables(response, project.model_dump(),  position)
        return response

    # Cannot be async because it will be used as Celeri
    @staticmethod
    def generate_ai_table_edits(id, user_request):
        project = ProjectService.get_project(id)
        system_message = PromptGenerator.get_ai_edit_table_system_prompt(project, user_request['currentTable'])
        user_message = user_request['prompt']
        openai_response = services_utils.prompt_openai(ProjectService.settings.openai_model, system_message, user_message)
        response = json.loads(openai_response)
        services_utils.generate_id_if_missing(response['columns'])
        return response
    
    # Cannot be async because it will be used as Celeri
    @staticmethod
    def generate_image(id, questions):
        prompt = PromptGenerator.get_image_generation_prompt(questions)
        services_utils.generate_image(id, prompt)

    @staticmethod
    def get_project_imagae(id: str):
    # Define the path where images are stored
        print(os.getcwd())
        default_image = "project_images/default.png"
        image_path = f"project_images/{id}.png"

        # Check if the image exists
        if os.path.exists(image_path):
            return FileResponse(image_path)
        else:
            return FileResponse(default_image)