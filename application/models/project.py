from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

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

class DBTechnology(Enum):
    SNOWFLAKE = 1
    DATABRICKS = 2
    MSSQL = 3
    MYSQL = 4

class ProjectType(Enum):
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
    dbTechnology: DBTechnology
    projectType: ProjectType
    active: bool
    owner: Owner
    lastModified: int

class ProjectCreate(BaseModel):
    id: str
    name: str
    #dbTechnology: DBTechnology
    dbTechnology: int
    #projectType: ProjectType
    projectType: str
    questions: str
    additionalInfo: Optional[str] = None
    namingRules: Optional[str] = None