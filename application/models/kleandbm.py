from pydantic import BaseModel
from typing import List, Optional, Union, Any
from enum import Enum, IntEnum

class Job(BaseModel):
    jobId: str

class JobResult(BaseModel):
    jobId: str
    status: str
    #how to do this for when tables are suggested
    result: Any = None

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
    projectId: Optional[str] = None

class TableUpdate(BaseModel):
    id: str = None
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    columns: Optional[List[Column]] = None
    lastModified: Optional[int] = None
    projectId: Optional[str] = None

class Node(BaseModel):
    id: str
    projectId: Optional[str] = None
    active: bool
    lastModified: int
    tableId: str
    x: float
    y: float

class NodeUpdate(BaseModel):
    id: Optional[str] = None
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
    label: Optional[str] = None

class RelationshipUpdate(BaseModel):
    id: Optional[str] = None
    projectId: Optional[str] = None
    parentColumn: Optional[str] = None
    childColumn: Optional[str] = None
    active: Optional[bool] = True
    identifying: Optional[bool] = None
    label: Optional[str] = None

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
    description: str
    owner: Owner

class ProjectUpdate(BaseModel):
    id: Optional[str] = None
    active: Optional[bool] = True
    name: Optional[str] = None
    description: Optional[str] = None

class DatabaseTechnology(BaseModel):
    id: DBTechnologyId
    name: str
    dataTypes: List[str]

class SQLResponse(BaseModel):
    sql: str

class Position(BaseModel):
    x: float
    y: float

class AITablesUpdate(BaseModel):
    prompt: str
    position: Position


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

