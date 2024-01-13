from pydantic import BaseModel
from typing import List, Optional
from enum import Enum, IntEnum
import application.constants as constants

class Job(BaseModel):
    jobId: str

class Column(BaseModel):
    id: str
    name: str
    description: str
    dataType: str
    active: bool
    primaryKey: bool

class Table(BaseModel):
    id: str
    name: str
    description: str
    active: bool
    columns: List[Column]

class Position(BaseModel):
    x: float
    y: float

class Relationship(BaseModel):
    id: str
    parentColumn: str
    childColumn: str
    active: bool
    identifying: bool

class DBTechnologyId(IntEnum):
    SNOWFLAKE = 1
    DATABRICKS = 2
    MSSQL = 3
    MYSQL = 4

class ProjectType(str, Enum):
    ANALYTICAL = "analytical"
    TRANSACTIONAL = "transactional"

class Owner(BaseModel):
    id: str
    name: str

class Project(BaseModel):
    id: str
    description: str
    tables: List[Table]
    relationships: List[Relationship]
    dbTechnology: DBTechnologyId
    projectType: ProjectType
    active: bool
    owner: Owner
    lastModified: int

class ProjectCreate(BaseModel):
    id: str
    name: str
    dbTechnology: DBTechnologyId
    projectType: ProjectType
    questions: str
    additionalInfo: Optional[str] = None
    namingRules: Optional[str] = None

class DatabaseTechnology(BaseModel):
    id: DBTechnologyId
    name: str
    dataTypes: List[str]

class DatabaseTechnologies:
    @staticmethod
    def get_technology_by_id(technology_id: DBTechnologyId) -> Optional[DatabaseTechnology]:
        for technology in constants.DATABASE_TECHNOLOGIES:
            if technology.id == technology_id:
                return technology
        return None
    
class PromptGenerator:
    @staticmethod
    def get_prompt(key, **kwargs):
        template = constants.OPENAI_PROMPT_TEMPLATES.get(key)
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
            model_type = "a normalized model"
            type_2_dimension = "If Type 2 dimension is needed include a surrogate key; this surrogage key should be used for linking to other tables. Natural business keys should default to an integer-like data type.\n\n\
Fact tables should not have a record id; the ids from the dimensions should be sufficient.\n\n"
        return PromptGenerator.get_prompt("createProjectSystemMessage", project_type = new_project.projectType, \
                                                                        database_technology_name = database_technology.name, \
                                                                        model_type = model_type, \
                                                                        type_2_dimension = type_2_dimension, \
                                                                        data_types = (", ".join(database_technology.dataTypes)))

    @staticmethod
    def get_create_project_user_prompt(new_project: ProjectCreate):
        naming_rules = ""
        additional_info = ""
        if not new_project.namingRules:
            naming_rules = constants.DEFAULT_ANALYTICAL_NAMING_RULES if new_project.projectType == ProjectType.ANALYTICAL else constants.DEFAULT_TRANSACTIONAL_NAMING_RULES
        else:
            naming_rules = new_project.namingRules
        additional_info = constants.DEFAULT_ADDITIONAL_INFORMATION if not new_project.additionalInfo else new_project.additionalInfo        
        return PromptGenerator.get_prompt("createProjectUserMessage", questions = new_project.questions, \
                                                                        naming_rules = naming_rules, \
                                                                        additional_info = additional_info)