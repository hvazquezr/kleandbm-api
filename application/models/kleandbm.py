from pydantic import BaseModel, Field
from typing import List, Optional, Any
from enum import Enum, IntEnum
from datetime import datetime


class Job(BaseModel):
    jobId: str

class JobResult(BaseModel):
    jobId: str
    status: str
    #how to do this for when tables are suggested
    result: Any = None

class NodeType(str, Enum):
    TABLE = "tableNode"
    NOTE = "noteNode"

class Column(BaseModel):
    id: str
    name: str
    description: str
    dataType: str
    maxLength:  Optional[int] = None
    precision:  Optional[int] = None
    scale:  Optional[int] = None
    primaryKey:  Optional[bool] = None
    canBeNull:  Optional[bool] = None
    autoIncrementOn:  Optional[bool] = None

class Table(BaseModel):
    id: str
    name: str
    description: str
    active: bool
    columns: List[Column]
    lastModified: datetime
    projectId: Optional[str] = None

class TableUpdate(BaseModel):
    id: str = None
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    columns: Optional[List[Column]] = None
    lastModified: Optional[datetime] = None
    projectId: Optional[str] = None
    changeId: str

class Node(BaseModel):
    id: str
    projectId: Optional[str] = None
    type: Optional[NodeType] = None
    active: bool
    lastModified: datetime
    tableId: Optional[str] = None
    text: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    x: float
    y: float

class NodeUpdate(BaseModel):
    id: Optional[str] = None
    projectId: Optional[str] = None
    type: Optional[NodeType] = None
    active: Optional[bool] = True
    tableId: Optional[str] = None
    text: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    changeId: str

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
    changeId: str

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
    name: Optional[str] = None

class Change(BaseModel):
    id: str = Field(validation_alias='_id')
    timestamp: datetime
    name: Optional[str] = None

    class Config:
        extra = 'ignore'

class ChangeUpdate(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    projectId: Optional[str] = None

class ChangeDate(BaseModel):
    year: int
    month: int
    day: int

class ProjectHeader(BaseModel):
    id: str = Field(valiation_alias='_id')
    name: str
    description: str
    dbTechnology: DBTechnologyId
    projectType: ProjectType
    active: bool
    owner: Owner
    lastChange: Change

    class Config:
        extra = 'ignore'

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
    changeId: str
    lastChange: Change



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
    changeId: str
    owner: Optional[Owner] = None

class ProjectUpdate(BaseModel):
    id: Optional[str] = None
    active: Optional[bool] = True
    name: Optional[str] = None
    description: Optional[str] = None
    changeId: str

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
    
    @staticmethod
    def generate_ddl_sql(project):
        if project.dbTechnology == DBTechnologyId.SNOWFLAKE:
            return DatabaseTechnologies.generate_ddl_snowflake(project)
        elif project.dbTechnology == DBTechnologyId.DATABRICKS:
            return DatabaseTechnologies.generate_ddl_databricks(project)
        elif project.dbTechnology == DBTechnologyId.MSSQL:
            return DatabaseTechnologies.generate_ddl_sql_server(project)
        elif project.dbTechnology == DBTechnologyId.MYSQL:
            return DatabaseTechnologies.generate_ddl_mysql(project)

    @staticmethod
    def generate_ddl_snowflake(data):
        ddl_statements = []

        # Generate DDL for tables
        for table in data.tables:  # Changed to attribute access
            create_statement = f"CREATE TABLE {table.name} (\n"  # Changed to attribute access
            col_definitions = []
            pk = []

            for col in table.columns:  # Changed to attribute access
                col_def = f"    {col.name} {col.dataType}"  # Changed to attribute access
                if col.dataType.upper() == 'VARCHAR' and col.maxLength:  # Changed to attribute access
                    col_def += f"({col.maxLength})"  # Changed to attribute access
                elif col.dataType.upper() in ['DECIMAL', 'NUMBER', 'FLOAT'] and col.precision:  # Changed to attribute access
                    col_def += f"({col.precision}"  # Changed to attribute access
                    if col.scale:  # Changed to attribute access
                        col_def += f", {col.scale})"  # Changed to attribute access
                    else:
                        col_def += ")"
                if not col.canBeNull:  # Changed to attribute access
                    col_def += " NOT NULL"
                col_definitions.append(col_def)
                if col.primaryKey:  # Changed to attribute access
                    pk.append(col.name)  # Changed to attribute access

            if pk:
                pk_statement = f"\n    PRIMARY KEY ({', '.join(pk)})"
                col_definitions.append(pk_statement)

            create_statement += ",\n".join(col_definitions)
            create_statement += "\n);"
            ddl_statements.append(create_statement)

            # Add table comment
            ddl_statements.append(f"COMMENT ON TABLE {table.name} IS '{table.description}';")  # Changed to attribute access

            # Add column comments
            for col in table.columns:  # Changed to attribute access
                ddl_statements.append(f"COMMENT ON COLUMN {table.name}.{col.name} IS '{col.description}';")  # Changed to attribute access

        # Generate DDL for relationships (assuming foreign key constraints are desired)
        for rel in data.relationships:
                parent_table_name, parent_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.parentColumn)
                child_table_name, child_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.childColumn)
                
                if parent_table_name and child_table_name and parent_column_name and child_column_name:
                    ddl_statements.append(f"ALTER TABLE {child_table_name} "
                                        f"ADD CONSTRAINT FK_{child_table_name}_{parent_table_name} "
                                        f"FOREIGN KEY ({child_column_name}) "
                                        f"REFERENCES {parent_table_name}({parent_column_name});")

        return "\n\n".join(ddl_statements)

    @staticmethod
    def generate_ddl_sql_server(data):
        ddl_statements = []

        # Generate DDL for tables
        for table in data.tables:
            create_statement = f"CREATE TABLE {table.name} (\n"
            col_definitions = []
            pk = []

            for col in table.columns:
                # Check for autoIncrement property
                if col.autoIncrementOn:
                    auto_increment = " IDENTITY(1,1)"
                else:
                    auto_increment = ""

                col_def = f"    {col.name} {col.dataType}{auto_increment}"
                if col.dataType.upper() == 'VARCHAR' and col.maxLength:
                    col_def += f"({col.maxLength})"
                elif col.dataType.upper() in ['DECIMAL', 'NUMERIC', 'MONEY', 'SMALLMONEY', 'FLOAT', 'REAL'] and col.precision:
                    col_def += f"({col.precision}"
                    if col.scale:
                        col_def += f", {col.scale})"
                    else:
                        col_def += ")"
                if not col.canBeNull:
                    col_def += " NOT NULL"
                col_definitions.append(col_def)
                if col.primaryKey:
                    pk.append(col.name)

            if pk:
                # In SQL Server, IDENTITY should be used on the primary key column if autoIncrement is specified
                pk_statement = f"    CONSTRAINT PK_{table.name} PRIMARY KEY ({', '.join(pk)})"
                col_definitions.append(pk_statement)

            create_statement += ",\n".join(col_definitions)
            create_statement += "\n)"
            ddl_statements.append(create_statement)

        # Generate comments statements
        for table in data.tables:
            # Add table description
            ddl_statements.append(f"EXEC sp_addextendedproperty "
                                  f"'MS_Description', '{table.description}', "
                                  f"'SCHEMA', 'dbo', 'TABLE', '{table.name}';")
            
            # Add column descriptions
            for col in table.columns:
                ddl_statements.append(f"EXEC sp_addextendedproperty "
                                      f"'MS_Description', '{col.description}', "
                                      f"'SCHEMA', 'dbo', 'TABLE', '{table.name}', 'COLUMN', '{col.name}';")

        # Generate DDL for relationships
        for rel in data.relationships:
            parent_table_name, parent_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.parentColumn)
            child_table_name, child_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.childColumn)
            
            if parent_table_name and child_table_name and parent_column_name and child_column_name:
                ddl_statements.append(f"ALTER TABLE {child_table_name} "
                                      f"ADD CONSTRAINT FK_{child_table_name}_{parent_table_name} "
                                      f"FOREIGN KEY ({child_column_name}) "
                                      f"REFERENCES {parent_table_name}({parent_column_name});")
                
        return "\n\n".join(ddl_statements)
    

    @staticmethod
    def generate_ddl_mysql(data):
        ddl_statements = []

        # Generate DDL for tables
        for table in data.tables:
            create_statement = f"CREATE TABLE `{table.name}` (\n"
            col_definitions = []
            pk = []

            for col in table.columns:
                col_def = f"`{col.name}` {col.dataType}"
                if col.dataType.upper() == 'VARCHAR' and col.maxLength:
                    col_def += f"({col.maxLength})"
                elif col.dataType.upper() in ['DECIMAL', 'NUMERIC', 'FLOAT', 'DOUBLE'] and col.precision:
                    col_def += f"({col.precision}"
                    if col.scale:
                        col_def += f", {col.scale})"
                    else:
                        col_def += ")"
                if col.autoIncrementOn:
                    col_def += " AUTO_INCREMENT"
                if not col.canBeNull:
                    col_def += " NOT NULL"
                if col.description:
                    col_def += f" COMMENT '{col.description}'"
                col_definitions.append(col_def)
                if col.primaryKey:
                    pk.append(col.name)

            if pk:
                pk_statement = f",\n    PRIMARY KEY (`{'`, `'.join(pk)}`)"
                col_definitions.append(pk_statement)

            create_statement += ",\n".join(col_definitions)
            create_statement += "\n);"
            if table.description:
                create_statement += f"\n) COMMENT='{table.description}';"
            ddl_statements.append(create_statement)

        # Generate DDL for relationships
        for rel in data.relationships:
            parent_table_name, parent_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.parentColumn)
            child_table_name, child_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.childColumn)
            
            if parent_table_name and child_table_name and parent_column_name and child_column_name:
                ddl_statements.append(f"ALTER TABLE `{child_table_name}` "
                                      f"ADD CONSTRAINT `FK_{child_table_name}_{parent_table_name}` "
                                      f"FOREIGN KEY (`{child_column_name}`) "
                                      f"REFERENCES `{parent_table_name}`(`{parent_column_name}`);")

        return "\n\n".join(ddl_statements)
    

    @staticmethod
    def generate_ddl_databricks(data):
        ddl_statements = []

        # Generate DDL for tables with primary key support
        for table in data.tables:
            create_statement = f"CREATE TABLE IF NOT EXISTS `{table.name}` (\n"
            col_definitions = []
            primary_keys = []
            
            for col in table.columns:
                col_def = f"`{col.name}` {col.dataType}"
                if col.maxLength and col.dataType.upper() == 'VARCHAR':
                    col_def += f"({col.maxLength})"
                elif col.precision and col.dataType.upper() in ['DECIMAL']:
                    col_def += f"({col.precision}, {col.scale if col.scale else 0})"
                
                col_definitions.append(col_def)
                
                if col.primaryKey:
                    primary_keys.append(f"`{col.name}`")

            # Add column definitions
            create_statement += ",\n".join(col_definitions)

            # Add primary key constraint if defined
            if primary_keys:
                create_statement += f",\nPRIMARY KEY ({', '.join(primary_keys)})"
            
            create_statement += f"\n)"

            # Add table comment if exists
            if table.description:
                create_statement += f"\nCOMMENT '{table.description}'"
            
            ddl_statements.append(create_statement)

            # Add column comments
            for col in table.columns:
                if col.description:
                    ddl_statements.append(f"ALTER TABLE `{table.name}` CHANGE COLUMN `{col.name}` COMMENT '{col.description}';")

        # Generate DDL for foreign key relationships
        for rel in data.relationships:
            parent_table_name, parent_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.parentColumn)
            child_table_name, child_column_name = DatabaseTechnologies.find_table_name_and_column_name_by_column_id(data, rel.childColumn)
            
            if parent_table_name and child_table_name and parent_column_name and child_column_name:
                ddl_statements.append(f"ALTER TABLE `{child_table_name}` ADD CONSTRAINT `fk_{child_table_name}_{parent_table_name}` FOREIGN KEY (`{child_column_name}`) REFERENCES `{parent_table_name}`(`{parent_column_name}`);")

        return "\n\n".join(ddl_statements)
    
    @staticmethod
    def find_table_name_and_column_name_by_column_id(data, column_id):
        """
        Find the table name and column name by the column's ID.

        Args:
        data: The database object containing tables and columns.
        column_id: The ID of the column to find.

        Returns:
        A tuple of (table_name, column_name).
        """
        for table in data.tables:
            for col in table.columns:
                if col.id == column_id:
                    return (table.name, col.name)
        return (None, None)
