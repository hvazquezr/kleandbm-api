import json
from confluent_kafka import Producer
from application.models.PromptGenerator import PromptGenerator
from application.models.kleandbm import Project, ProjectHeader, ProjectCreate, ProjectUpdate, NodeUpdate, TableUpdate, RelationshipUpdate, SQLResponse, DatabaseTechnologies, Owner, ChangeUpdate, Change
from application.config import get_settings
import services.utils as services_utils
from typing import List
from fastapi import HTTPException


class ProjectService:
    settings = get_settings()

    kafka_conf = {'bootstrap.servers': settings.kafka_server,
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': settings.kafka_username,
            'sasl.password': settings.kafka_password}

    producer = Producer(kafka_conf)

    @staticmethod
    async def check_user_allowed(project_id, user_paylod):
        filter = {
            'active': True, 
            'owner.id': user_paylod.get('sub'),
            '_id': project_id
        }
        project={
            'owner': 1, 
            '_id': 0
        }
        project = await services_utils.query_mongodb('project', filter, project)

        if len(project) == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        if project[0].get('owner').get('id') != user_paylod.get('sub'):
            raise HTTPException(status_code=403, detail="User does not have access to this project.")

    ## The kafka methods are here and not in utils so that the producer is here and remains open for performance reasons
    @staticmethod
    def kafka_produce(topic, key, value):
        # Due to this celeri/kafka-python issue the producer has to be local when called from a celeri worker
        # https://github.com/dpkp/kafka-python/issues/1098

        kafka_conf = {'bootstrap.servers': ProjectService.settings.kafka_server,
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': ProjectService.settings.kafka_username,
            'sasl.password': ProjectService.settings.kafka_password}

        producer = Producer(kafka_conf)
        producer.produce(topic, key=key, value=value)
        producer.flush()

    @staticmethod
    async def async_kafka_produce(topic, key, value):
        ProjectService.producer.produce(topic, key=key, value=value)
        ProjectService.producer.flush()

    # TODO: Change the return type to Project and handle that in Celeri
    @staticmethod
    def create_project(new_project: ProjectCreate, user_payload):
        project_id = new_project.id
        changeId = new_project.changeId
        system_message = PromptGenerator.get_create_project_sytem_prompt(new_project)
        user_message = PromptGenerator.get_create_project_user_prompt(new_project)
        raw_data_model = json.loads(services_utils.prompt_openai(ProjectService.settings.openai_model, system_message, user_message))
        # In some cases openai is returning an array; in that case it gathers the first element of the array
        if isinstance(raw_data_model, list):
            raw_data_model = raw_data_model[0]
        # @TODO: This should be of Project data Type
        # @TODO: Determine if it's best to move Save to the Project datatype
        suggested_data_model = services_utils.complete_project(project_id, raw_data_model)
        nodes = services_utils.generate_nodes(suggested_data_model, project_id)
        
        new_project.description = suggested_data_model['description']
        new_project.owner = Owner(id =  user_payload.get('sub'))
        ProjectService.kafka_produce('project-updates', project_id, new_project.model_dump_json(exclude_none=True))
        for table in suggested_data_model['tables']:
            table['changeId'] = changeId
            ProjectService.kafka_produce('table-updates', project_id, json.dumps(table)) # Saving tables

        for relationship in suggested_data_model['relationships']:
            relationship['changeId'] = changeId
            ProjectService.kafka_produce('relationship-updates', project_id, json.dumps(relationship)) # Saving relationsihps

        for node in nodes:
            node['changeId'] = changeId
            ProjectService.kafka_produce('node-updates', project_id, json.dumps(node)) # Saving node

        return suggested_data_model
    
    @staticmethod
    async def get_projects(user_paylod) -> List[ProjectHeader]:
        projects_json = await services_utils.get_projects_with_change(user_paylod.get('sub'))
        response_list = [ProjectHeader(**p) for p in projects_json]
        return response_list
    
    @staticmethod
    async def async_get_project(id, user_payload) -> Project:
        await ProjectService.check_user_allowed(id, user_payload)
        result_list = await services_utils.async_get_project_with_children(id)
        result = Project(**(result_list[0]))
        return result
    
    @staticmethod
    def get_project(id) -> Project:
        result_list = services_utils.get_project_with_children(id)
        result = Project(**(result_list[0]))
        return result

    @staticmethod
    async def get_project_changes(id, user_paylod) -> List[Change]:
        await ProjectService.check_user_allowed(id, user_paylod)

        filter = {
            'projectId': id
        }

        sort = {
            'timestamp': -1
        }

        changes_json = await services_utils.query_mongodb('change', filter = filter, sort = sort )

        response_list = [Change(**p) for p in changes_json]
        return response_list

    @staticmethod
    async def update_project(id, updated_project, user_payload) -> ProjectUpdate:
        await ProjectService.check_user_allowed(id, user_payload)
        updated_project.id = id
        await ProjectService.async_kafka_produce('project-updates', id, updated_project.model_dump_json(exclude_none=True))
        return updated_project
    
    @staticmethod
    async def delete_project(id, user_payload):
        await ProjectService.check_user_allowed(id, user_payload)
        to_delete_project = ProjectUpdate(id = id, active=False)
        await ProjectService.async_kafka_produce('project-updates', id, to_delete_project.model_dump_json(exclude_none=True))

    @staticmethod
    async def update_node(project_id, node_id, updated_node, user_payload) -> NodeUpdate:
        await ProjectService.check_user_allowed(project_id, user_payload)
        updated_node.id = node_id
        await ProjectService.async_kafka_produce('node-updates', project_id, updated_node.model_dump_json(exclude_none=True))
        #await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified
        return updated_node

    @staticmethod
    async def delete_node(project_id, node_id, user_payload, changeId):
        await ProjectService.check_user_allowed(project_id, user_payload)
        to_delete_node = NodeUpdate(id = node_id, active=False, changeId = changeId)
        await ProjectService.async_kafka_produce('node-updates', project_id, to_delete_node.model_dump_json(exclude_none=True))
        #await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified

    @staticmethod
    async def update_table(project_id, table_id, updated_table, user_payload) -> TableUpdate:
        await ProjectService.check_user_allowed(project_id, user_payload)
        updated_table.id = table_id
        await ProjectService.async_kafka_produce('table-updates', project_id, updated_table.model_dump_json(exclude_none=True))
        #await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified
        return updated_table

    @staticmethod
    async def delete_table(project_id, table_id, user_payload, changeId):
        await ProjectService.check_user_allowed(project_id, user_payload)
        to_delete_table = TableUpdate(id = table_id, active=False, changeId = changeId)
        await ProjectService.async_kafka_produce('table-updates', project_id, to_delete_table.model_dump_json(exclude_none=True))
        #await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified

    @staticmethod
    async def update_relationship(project_id, relationship_id, updated_relationship, user_payload) -> RelationshipUpdate:
        await ProjectService.check_user_allowed(project_id, user_payload)
        updated_relationship.projectId = project_id
        updated_relationship.id = relationship_id
        await ProjectService.async_kafka_produce('relationship-updates', project_id, updated_relationship.model_dump_json(exclude_none=True))
        #await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified
        return updated_relationship

    @staticmethod
    async def delete_relationship(project_id, relationship_id, user_payload, changeId):
        await ProjectService.check_user_allowed(project_id, user_payload)
        to_delete_relationship = RelationshipUpdate(id = relationship_id, active=False, changeId = changeId)
        await ProjectService.async_kafka_produce('relationship-updates', project_id, to_delete_relationship.model_dump_json(exclude_none=True))
        #await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps({'id': project_id})) # Touching project to update lastmodified

    @staticmethod
    async def get_project_sql(id, user_payload):
        project = (await ProjectService.async_get_project(id, user_payload))
        sql = DatabaseTechnologies.generate_ddl_sql(project)
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

    @staticmethod
    async def update_change_name(project_id, change_id, updated_change, user_payload) -> ChangeUpdate:
        await ProjectService.check_user_allowed(project_id, user_payload)
        updated_change.projectId = project_id
        updated_change.id = change_id
        await ProjectService.async_kafka_produce('change-updates', project_id, updated_change.model_dump_json(exclude_none=False))
        return updated_change