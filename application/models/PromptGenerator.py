import application.constants as app_constants
import application.utils as utils
from application.models.kleandbm import DatabaseTechnologies, Project, ProjectCreate, ProjectType


import json


class PromptGenerator:
    @staticmethod
    def get_prompt(key, **kwargs):
        template = app_constants.OPENAI_PROMPT_TEMPLATES.get(key)
        return template.format(**kwargs)

    @staticmethod
    def get_explanation_prompt(topic):
        return PromptGenerator.get_prompt("explanationPrompt", topic=topic)

    @staticmethod
    def get_create_project_sytem_prompt(new_project: ProjectCreate):
        database_technology = DatabaseTechnologies.get_technology_by_id(new_project.dbTechnology)
        model_type = ""
        type_2_dimension = ""
        if  new_project.projectType == ProjectType.ANALYTICAL:
            model_type = "a denormalized model"
            type_2_dimension = "If Type 2 dimension is needed include a surrogate key; this surrogage key should be used for linking to other tables. Natural business keys should default to an integer-like data type.\n\n\
Fact tables should not have a record id or primary keys; the ids from the dimensions should be sufficient.\n\n"
        return PromptGenerator.get_prompt("createProjectSystemMessage", project_type = new_project.projectType.value, \
                                                                        db_technology_name = database_technology.name, \
                                                                        model_type = model_type, \
                                                                        type_2_dimension = type_2_dimension, \
                                                                        data_types = (", ".join(database_technology.dataTypes)))

    @staticmethod
    def get_create_project_user_prompt(new_project: ProjectCreate):
        naming_rules = ""
        additional_info = ""
        if not new_project.namingRules:
            naming_rules = app_constants.DEFAULT_ANALYTICAL_NAMING_RULES if new_project.projectType == ProjectType.ANALYTICAL else app_constants.DEFAULT_TRANSACTIONAL_NAMING_RULES
        else:
            naming_rules = new_project.namingRules
        additional_info = app_constants.DEFAULT_ADDITIONAL_INFORMATION if not new_project.additionalInfo else new_project.additionalInfo
        return PromptGenerator.get_prompt("createProjectUserMessage", questions = new_project.questions, \
                                                                        naming_rules = naming_rules, \
                                                                        additional_info = additional_info)

    @staticmethod
    def get_sql_user_prompt(project: Project):
        return project.model_dump_json()

    @staticmethod
    def get_ai_add_table_system_prompt(project: Project):
        database_technology = DatabaseTechnologies.get_technology_by_id(project.dbTechnology)
        return PromptGenerator.get_prompt("suggestNewTablesPrompt", db_technology_name = database_technology.name, data_types = (", ".join(database_technology.dataTypes)))

    @staticmethod
    def get_ai_add_table_user_prompt(project: Project, prompt: str):
        project_dict = project.model_dump()
        project_tables = utils.remove_attributes(project_dict['tables'], ["id", "active", "lastModified", "projectId"])
        return prompt + '\n\n' + json.dumps(project_tables)
    
    @staticmethod
    def get_ai_edit_table_system_prompt(project: Project, table_structure):
        database_technology = DatabaseTechnologies.get_technology_by_id(project.dbTechnology)
        structure = "the json structure provided"
        if (len(table_structure['columns'])==0):
            structure = app_constants.OPENAI_PROMPT_TEMPLATES["referenceTableStructure"]
        return PromptGenerator.get_prompt("editTablePrompt", db_technology_name = database_technology.name, \
                                          data_types = (", ".join(database_technology.dataTypes)), \
                                          reference_structure=structure, \
                                          table_structure = json.dumps(table_structure))
    
    @staticmethod
    def get_update_naming_rules_system_prompt():
        return PromptGenerator.get_prompt("updateNamingRulesSytemMessage")
    
    @staticmethod
    def get_update_naming_rules_user_prompt(naming_rules, tables_array):
        return PromptGenerator.get_prompt("updateNamingRulesUserMessage", naming_rules = naming_rules, tables_array=tables_array)