from application.models.kleandbm import DatabaseTechnology, DBTechnologyId


DATABASE_TECHNOLOGIES = [
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

OPENAI_PROMPT_TEMPLATES = {
    'createProjectSystemMessage': "Act as a data architect. Design a relational database and provide a project \
description for a {project_type} system in {db_technology_name} \
using {model_type} based on a series of business questions, a set of naming rules, and some other information. \n\n \
The responses should be a JSON array of tables with the format {description:project description (no more than 250 characters), tables:[{name:tableName, description:table desciption (no more than 100 characters), columns:[{name:Column Name, description: column description (no more than 100 characters), primaryKey: (true if it is primary key), dataType: data type},..]]}. \n\n \
{type_2_dimension}\
Only include the following datatypes: {data_types}",

    'createProjectUserMessage': "The business questions are:\n {questions}\n\n\
Adhere to the following naming rules: {naming_rules}\n\n\
Also consider the following information:\n{additional_info}",

    'generateSqlPrompt': "Act as an expert sql programmer and data architect. The following is a json representation of a database model for {db_technology_name}. Generate the SQL  DDL code to generate these objects. Infere relationships by referencing childColumn and parentColumn in the relationship elements. Do not include any commentary or explanation,  exclusively just the code and comments within it.",

    'suggestNewTablesPrompt': "Act as an expert sql programmer and data architect. You will be provided a json representation of a database model for {db_technology_name}, instructions to create a new table, or set of new tables to complement this model. Provide the structure for these tables in a json array referencing the json structure below. Do not include any commentary or explanation. \nConsider the following data types: {data_types}",

    'editTablePrompt': "Act as an expert sql programmer and data architect. You will be provided a json representation of a table for {db_technology_name} and instructions to modify the table structure or description. Provide the structure for suggested modified table in a json object referencing the json structure provided. Newly added columns should not have the id attribute.\n\
If a column is renamed but preserves the intent of the previous name retain the same id.\n\
Consider the following data types: {db_technology_name}\n\
Current table structure:\n",

    'referenceTableStructure':" this json structure:\n\
 {\n\
'columns': [\n\
                    {\n\
                        'active': true,\n\
                        'dataType': (suggested data type),\n\
                        'description': (Description for column),\n\
                        'id': (Omit if it is newly suggested column),\n\
                        'name': (name for column),\n\
                        'primaryKey': (true if column is intended to be primary key)\n\
                    },\n\
                ],\n\
                'description': (Description for table),\n\
                'name': (Suggested name)\n\
}"    
}

DEFAULT_ANALYTICAL_NAMING_RULES = "Use DIM prefix for dimension tables and FACT prefix for fact tables.\n\
Use underscore to separate words.\n\
Table names all in uppercase.\n\
Column names all lower case."

DEFAULT_TRANSACTIONAL_NAMING_RULES = "Camelcase"

DEFAULT_ADDITIONAL_INFORMATION =  "No additional information"