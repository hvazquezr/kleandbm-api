OPENAI_PROMPT_TEMPLATES = {
    'updateNamingRulesSytemMessage': "Act as a data architect. You will receive a json array of tables with name and description. It will also contain an array of \
columns. Also you will receive a series of naming rules. Return a jason array with the names and descriptions adjusted to the new naming \
rules. Ensure the json array is wrapped with ```json at the beginning and end of the array and ``` at the end of the array.",
    'updateNamingRulesUserMessage': " \nTables: {tables_array} \nNaming rules:{naming_rules}",
    'createProjectSystemMessage': "Act as a data architect. Design a relational database and provide a project \
description for a {project_type} database in {db_technology_name} (Don't include the name of the technology in the description)\
using {model_type} based on a series of business questions, a set of naming rules, and some other information.\n\n\
The response should be a JSON array of tables with the format {{description:project description (no more than 250 characters), tables:[{{name:tableName, description:table desciption (no more than 100 characters), columns:[{{name:Column Name, description: column description (no more than 100 characters), primaryKey: (true if it is primary key), dataType: data type, maxLength: (if applicable), precision: (if applicable), scale: (if applicable), canBeNull: (boolean to indicate if it can hold null values)}},..]]}}}}.\n\n\
{type_2_dimension}\
Only include the following datatypes: {data_types}\n\n\
Only include the json array and not additional context.",

    'createProjectUserMessage': "The business questions are:\n {questions}\n\n\
Adhere to the following naming rules: {naming_rules}\n\n\
Also consider the following information:\n{additional_info}",

    'suggestNewTablesPrompt': "Act as an expert sql programmer and data architect. You will be provided a json representation of a database model for {db_technology_name}, instructions to create a new table, or set of new tables to complement this model. Provide the structure for these tables in a json array referencing the json structure below. Do not include any commentary or explanation. \nConsider the following data types: {data_types}",

    'editTablePrompt': "Act as an expert sql programmer and data architect. You will be provided a json representation of a table for {db_technology_name} and instructions to modify the table structure or description. Provide the structure for suggested modified table in a json object referencing {reference_structure}. Newly added columns should not have the id attribute.\n\
If a column is renamed but preserves the intent of the previous name retain the same id.\n\
Consider the following data types: {data_types}\n\
Current table structure:\n\n\n{table_structure}",

    'referenceTableStructure':" this json structure:\n\
 {\n\
'columns': [\n\
                    {\n\
                        'active': true,\n\
                        'dataType': (suggested data type),\n\
                        'description': (Description for column),\n\
                        'id': (Omit if it is newly suggested column),\n\
                        'name': (name for column),\n\
                        'primaryKey': (true if column is intended to be primary key),\n\
                        'maxLength': (if applicable),\n\
                        'precision': (if applicable),\n\
                        'scale': (if applicable),\n\
                    },\n\
                ],\n\
                'description': (Description for table),\n\
                'name': (Suggested name)\n\
}"}

DEFAULT_ANALYTICAL_NAMING_RULES = "Use DIM prefix for dimension tables and FACT prefix for fact tables.\n\
Use underscore to separate words.\n\
Table names all in uppercase.\n\
Column names all lower case."

DEFAULT_TRANSACTIONAL_NAMING_RULES = "Camelcase"

DEFAULT_ADDITIONAL_INFORMATION =  "No additional information"