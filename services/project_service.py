import json
from confluent_kafka import Producer
from application.models.PromptGenerator import PromptGenerator
from application.models.kleandbm import Project, ProjectHeader, ProjectCreate, ProjectUpdate, NodeUpdate, TableUpdate, RelationshipUpdate, SQLResponse, DatabaseTechnologies, Owner, ChangeUpdate, Change, ProjectId
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
        
    @staticmethod
    async def check_if_project_exists(project_id, change_id, user_paylod):
        filter = {
            '_id': project_id,
            'changeId': change_id,
            'active': True
        }
        project = await services_utils.query_mongodb('project', filter)
        if len(project) == 0:
            raise HTTPException(status_code=404, detail="Project not found")

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
    async def async_get_project_by_change(id, change_id, user_payload) -> Project:
        await ProjectService.check_user_allowed(id, user_payload)
        result_list = await services_utils.async_get_project_by_change(id, change_id)
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
    async def get_project_sql(id, change_id, user_payload):
        project = (await ProjectService.async_get_project_by_change(id, change_id, user_payload))
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
    
    # Cannot be async because it will be used as Celeri
    # TODO: Finish this call
    # Send to OpenAI the list of tables and relationships to ask to change according to new rules
    # Update the list of tables in mongodb for name and description
    @staticmethod
    def update_naming_rules(id, user_request):
        project = ProjectService.get_project(id)
        change_id = user_request['changeId']
        naming_rules = user_request['namingRules']
        system_message = PromptGenerator.get_update_naming_rules_system_prompt()
        user_message = PromptGenerator.get_update_naming_rules_user_prompt(naming_rules, services_utils.lean_table_attributes(project.tables))
        openai_response = services_utils.prompt_openai(ProjectService.settings.openai_model, system_message, user_message)
        renamed_tables = json.loads(openai_response)
        updated_tables = services_utils.update_table_names(project.tables, renamed_tables)
        updated_tables_dict = [table.model_dump() for table in updated_tables]
        # Iterate through the updated_tables and save them
        for table in updated_tables_dict:
            table['changeId'] = change_id
            del table['lastModified']
            ProjectService.kafka_produce('table-updates', id, json.dumps(table))
        
        ProjectService.kafka_produce('project-updates', id, json.dumps({'id':id, 'namingRules': naming_rules, 'changeId': change_id}))
        # Then find a way to return the project
        return renamed_tables

    @staticmethod
    async def update_change_name(project_id, change_id, updated_change, user_payload) -> ChangeUpdate:
        await ProjectService.check_user_allowed(project_id, user_payload)
        updated_change.projectId = project_id
        updated_change.id = change_id
        await ProjectService.async_kafka_produce('change-updates', project_id, updated_change.model_dump_json(exclude_none=False))
        return updated_change
    
    @staticmethod
    async def clone_project_by_change(project_id, change_id, new_change_id, user_payload) -> ProjectId:
        await ProjectService.check_user_allowed(project_id, user_payload)
        cloned_project = (await services_utils.async_clone_project_by_change(project_id, change_id))
        cloned_project_id = cloned_project['id']
        top_level_project_data = {k: cloned_project[k] for k in cloned_project if k not in ['tables', 'nodes', 'relationships']}
        top_level_project_data['name'] = top_level_project_data['name'] + " Copy"
        top_level_project_data['changeId'] = new_change_id
        top_level_project_data['_id'] = top_level_project_data['id']
        top_level_project_data['owner'] = {'id': user_payload.get('sub')}


        for table in cloned_project.get('tables', []):
            table['changeId'] = new_change_id
            table['_id'] = table['id']
            await ProjectService.async_kafka_produce('table-updates', cloned_project_id, json.dumps(table))

        for node in cloned_project.get('nodes', []):
            node['changeId'] = new_change_id
            node['_id'] = node['id']
            await ProjectService.async_kafka_produce('node-updates', cloned_project_id, json.dumps(node))

        for relationship in cloned_project.get('relationships', []):
            relationship['changeId'] = new_change_id
            relationship['_id'] = relationship['id']
            await ProjectService.async_kafka_produce('relationship-updates', cloned_project_id, json.dumps(relationship))

        await ProjectService.async_kafka_produce('project-updates', cloned_project_id, json.dumps(top_level_project_data))

        return ProjectId(id=cloned_project_id).model_dump()
    
    @staticmethod
    async def restore_project_by_change(project_id, change_id, new_change_id, user_payload) -> ProjectId:
        async def deactivate_missing_items(topic, current_items, previous_items):
            previous_ids = {item['id'] for item in previous_items}
            for item in current_items:
                if item['id'] not in previous_ids:
                    await ProjectService.async_kafka_produce(topic, project_id, json.dumps({'id': item['id'], 'active': False, 'changeId':  new_change_id}))

        async def persist_collections(topic, previous_items):
            for prev_item in previous_items:
                prev_item['changeId'] = new_change_id
                prev_item['_id'] = prev_item['id']
                del prev_item['lastModified']
                await ProjectService.async_kafka_produce(topic, project_id, json.dumps(prev_item))


        await ProjectService.check_user_allowed(project_id, user_payload)
        previous_version = (await services_utils.async_get_project_by_change(project_id, change_id))[0]
        current_version = (await services_utils.async_get_project_with_children(project_id))[0]

        top_level_project_data = {k: previous_version[k] for k in previous_version if k not in ['tables', 'nodes', 'relationships']}
        top_level_project_data['changeId'] = new_change_id
        top_level_project_data['_id'] = top_level_project_data['id']
        top_level_project_data['owner'] = {'id': user_payload.get('sub')}
        del top_level_project_data['lastModified']
        del top_level_project_data['lastChange']

        # Deactivate missing tables, nodes, and relationships
        await deactivate_missing_items('table-updates', current_version['tables'], previous_version['tables'])
        await deactivate_missing_items('node-updates', current_version['nodes'], previous_version['nodes'])
        await deactivate_missing_items('relationship-updates', current_version['relationships'], previous_version['relationships'])

        # Persist previous version items
        await persist_collections('table-updates', previous_version['tables'])
        await persist_collections('node-updates', previous_version['nodes'])
        await persist_collections('relationship-updates', previous_version['relationships'])

        await ProjectService.async_kafka_produce('project-updates', project_id, json.dumps(top_level_project_data))

        return ProjectId(id=project_id).model_dump()
