from pydantic import BaseModel
from typing import List, Optional
from enum import Enum, IntEnum
import application.constants as app_constants

class Job(BaseModel):
    jobId: str

class JobResult(BaseModel):
    jobId: str
    status: str
    #how to do this for when tables are suggested
    result: Optional[dict]

class Column(BaseModel):
    id: str
    name: str
    description: str
    dataType: str
    primaryKey: bool

class Table(BaseModel):
    id: str
    name: str
    description: str
    active: bool
    columns: List[Column]
    lastModified: int
    projectId: Optional[str]

class TableUpdate(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    columns: Optional[List[Column]] = None
    lastModified: Optional[int] = None
    projectId: Optional[str] = None

class Node(BaseModel):
    id: str
    projectId: Optional[str]
    active: bool
    lastModified: int
    tableId: str
    x: float
    y: float

class NodeUpdate(BaseModel):
    id: str
    projectId: Optional[str] = None
    active: Optional[bool] = True
    tableId: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None

class Relationship(BaseModel):
    id: str
    parentColumn: str
    childColumn: str
    active: bool
    identifying: bool
    label: Optional[str]

class RelationshipUpdate(BaseModel):
    id: str
    parentColumn: Optional[str]
    childColumn: Optional[str]
    active: Optional[bool] = True
    identifying: Optional[bool] = None
    label: Optional[str]

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

class ProjectHeader(BaseModel):
    id: str
    name: str
    description: str
    dbTechnology: DBTechnologyId
    projectType: ProjectType
    active: bool
    owner: Owner
    lastModified: int

class Project(BaseModel):
    id: str
    name: str
    description: str
    tables: List[Table]
    relationships: List[Relationship]
    nodes: List[Node]
    dbTechnology: DBTechnologyId
    projectType: ProjectType
    active: bool
    owner: Owner
    lastModified: int

class ProjectCreate(BaseModel):
    id: str
    active: bool = True
    name: str
    dbTechnology: DBTechnologyId
    projectType: ProjectType
    questions: str
    additionalInfo: Optional[str] = None
    namingRules: Optional[str] = None

class ProjectUpdate(BaseModel):
    id: str
    active: Optional[bool] = True
    name: Optional[str] = None

class DatabaseTechnology(BaseModel):
    id: DBTechnologyId
    name: str
    dataTypes: List[str]

class SQLResponse(BaseModel):
    sql: str

class DatabaseTechnologies:

    database_technologies_list = [
            DatabaseTechnology(
                id=DBTechnologyId.SNOWFLAKE,
                name="Snowflake",
                dataTypes=["VARCHAR", "NUMBER", "INTEGER", "FLOAT", "BOOLEAN", "DATE", "TIMESTAMP", "VARIANT", "OBJECT", "ARRAY", "GEOGRAPHY", "GEOMETRY"]
            ),
            DatabaseTechnology(
                id=DBTechnologyId.DATABRICKS,
                name="Databricks",
                dataTypes=["BIGINT", "BINARY", "BOOLEAN", "DATE", "DECIMAL", "DOUBLE", "FLOAT", "INT", "INTERVAL", "SMALLINT", "STRING", "TIMESTAMP", "TIMESTAMP_NTZ", "TINYINT", "ARRAY", "MAP", "STRUCT"]
            ),
            DatabaseTechnology(
                id=DBTechnologyId.MSSQL,
                name="SQL Server",
                dataTypes=["bigint", "int", "smallint", "tinyint", "bit", "decimal", "numeric", "money", "smallmoney", "float", "real", "datetime", "smalldatetime", "char", "varchar", "text", "nchar", "nvarchar", "ntext", "binary", "varbinary", "image", "cursor", "sql_variant", "table", "timestamp", "uniqueidentifier"]
            ),
            DatabaseTechnology(
                id=DBTechnologyId.MYSQL,
                name="MySql",
                dataTypes=["INTEGER", "INT", "SMALLINT", "TINYINT", "MEDIUMINT", "BIGINT", "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "DATE", "DATETIME", "TIMESTAMP", "TIME", "YEAR", "CHAR", "VARCHAR", "BINARY", "VARBINARY", "BLOB", "TEXT", "ENUM", "SET", "JSON"]
            )
]

    @staticmethod
    def get_technology_by_id(technology_id: DBTechnologyId) -> Optional[DatabaseTechnology]:
        for technology in DatabaseTechnologies.database_technologies_list:
            if technology.id == technology_id:
                return technology
        return None
    
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
            model_type = "a normalized model"
            type_2_dimension = "If Type 2 dimension is needed include a surrogate key; this surrogage key should be used for linking to other tables. Natural business keys should default to an integer-like data type.\n\n\
Fact tables should not have a record id; the ids from the dimensions should be sufficient.\n\n"
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
    def get_sql_system_prompt(project: Project):
        database_technology = DatabaseTechnologies.get_technology_by_id(project.dbTechnology)
        return PromptGenerator.get_prompt("generateSqlPrompt", db_technology_name = database_technology.name)
    
    @staticmethod
    def get_sql_user_prompt(project: Project):
        return project.model_dump_json()