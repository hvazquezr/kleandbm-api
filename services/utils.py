import re
from nanoid import generate
from openai import OpenAI
from application.config import get_settings
import networkx as nx
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

class ResponseType(str, Enum):
    JSON = "json"
    SQL = "sql"

# MongoDB Setup
async_client = AsyncIOMotorClient(get_settings().mongo_uri)
async_db = async_client[get_settings().mongo_db]

client = MongoClient(get_settings().mongo_uri)
db = client[get_settings().mongo_db]



async def query_mongodb(collection_name, filter, projection=None, sort=None):
    """
    Query a MongoDB collection and return the results.
    
    :param collection_name: The name of the collection to query
    :param filter_query: The filter query to apply
    :param projection: Optional projection to apply to the query
    :return: A list of documents that match the query
    """
    # Ensure the collection exists
    collection = async_db[collection_name]
    
    results = collection.find(filter = filter, sort = sort, projection = projection)
    
    # Convert the results to a list
    result_list = await results.to_list(length=None)
    
    return result_list


def get_project_with_children(project_id):
    pipeline = [
        {
            '$match': {'_id': project_id, 'active': True}
        },
        {
            '$lookup': {
                'from': 'table',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$and': [{'$eq': ['$projectId', '$$project_id']}, {'$eq': ['$active', True]}]}}}
                ],
                'as': 'tables'
            }
        },
        {
            '$lookup': {
                'from': 'node',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$and': [{'$eq': ['$projectId', '$$project_id']}, {'$eq': ['$active', True]}]}}}
                ],
                'as': 'nodes'
            }
        },
        {
            '$lookup': {
                'from': 'relationship',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$and': [{'$eq': ['$projectId', '$$project_id']}, {'$eq': ['$active', True]}]}}}
                ],
                'as': 'relationships'
            }
        },
        {
            '$lookup': {
                'from': 'change',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$projectId', '$$project_id']}}},
                    {'$sort': {'timestamp': -1}},
                    {'$limit': 1},
                    {
                        '$project': {
                            'id': '$_id',
                            'timestamp': 1,
                            'name': 1
                        }
                    }
                ],
                'as': 'lastChange'
            }
        },
        {
            '$addFields': {
                'id': '$_id',
                'lastChange': {'$arrayElemAt': ['$lastChange', 0]}
            }
        },
        {
            '$project': {
                '_id': 0,
                'tables._id': 0,
                'nodes._id': 0,
                'relationships._id': 0,
                'lastChange._id': 0
            }
        }
    ]

    result = list(db['project'].aggregate(pipeline))
    
    return result

async def async_get_project_with_children(project_id):
    pipeline = [
        {
            '$match': {'_id': project_id, 'active': True}
        },
        {
            '$lookup': {
                'from': 'table',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$and': [{'$eq': ['$projectId', '$$project_id']}, {'$eq': ['$active', True]}]}}}
                ],
                'as': 'tables'
            }
        },
        {
            '$lookup': {
                'from': 'node',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$and': [{'$eq': ['$projectId', '$$project_id']}, {'$eq': ['$active', True]}]}}}
                ],
                'as': 'nodes'
            }
        },
        {
            '$lookup': {
                'from': 'relationship',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$and': [{'$eq': ['$projectId', '$$project_id']}, {'$eq': ['$active', True]}]}}}
                ],
                'as': 'relationships'
            }
        },
        {
            '$lookup': {
                'from': 'change',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$projectId', '$$project_id']}}},
                    {'$sort': {'timestamp': -1}},
                    {'$limit': 1},
                    {
                        '$project': {
                            'id': '$_id',
                            'timestamp': 1,
                            'name': 1
                        }
                    }
                ],
                'as': 'lastChange'
            }
        },
        {
            '$addFields': {
                'id': '$_id',
                'lastChange': {'$arrayElemAt': ['$lastChange', 0]}
            }
        },
        {
            '$project': {
                '_id': 0,
                'tables._id': 0,
                'nodes._id': 0,
                'relationships._id': 0,
                'lastChange.id': 0
            }
        }
    ]

    result = await async_db['project'].aggregate(pipeline).to_list(length=None)
    
    return result

async def async_get_project_by_change(project_id, change_id):
    pipeline = [
    {
        '$match': {
            '_id': change_id,
            'projectId': project_id
        }
    }, {
        '$lookup': {
            'from': 'project_versions', 
            'let': {
                'changeTimestamp': '$timestamp', 
                'changeProjectId': '$projectId'
            }, 
            'pipeline': [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {
                                    '$eq': [
                                        '$id', '$$changeProjectId'
                                    ]
                                }, {
                                    '$lte': [
                                        '$lastModified', '$$changeTimestamp'
                                    ]
                                }
                            ]
                        }
                    }
                }, {
                    '$sort': {
                        'lastModified': -1
                    }
                }, {
                    '$limit': 1
                }
            ], 
            'as': 'projectVersion'
        }
    }, {
        '$unwind': '$projectVersion'
    }, {
        '$lookup': {
            'from': 'table_versions', 
            'let': {
                'projectId': '$projectVersion.id', 
                'timestamp': '$timestamp'
            }, 
            'pipeline': [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {
                                    '$eq': [
                                        '$projectId', '$$projectId'
                                    ]
                                }, {
                                    '$lte': [
                                        '$lastModified', '$$timestamp'
                                    ]
                                }
                            ]
                        }
                    }
                }, {
                    '$sort': {
                        'lastModified': -1
                    }
                }, {
                    '$group': {
                        '_id': '$id', 
                        'latest': {
                            '$first': '$$ROOT'
                        }
                    }
                }, {
                    '$replaceRoot': {
                        'newRoot': '$latest'
                    }
                }, {
                    '$match': {
                        'active': True
                    }
                }
            ], 
            'as': 'tables'
        }
    }, {
        '$lookup': {
            'from': 'node_versions', 
            'let': {
                'projectId': '$projectVersion.id', 
                'timestamp': '$timestamp'
            }, 
            'pipeline': [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {
                                    '$eq': [
                                        '$projectId', '$$projectId'
                                    ]
                                }, {
                                    '$lte': [
                                        '$lastModified', '$$timestamp'
                                    ]
                                }
                            ]
                        }
                    }
                }, {
                    '$sort': {
                        'lastModified': -1
                    }
                }, {
                    '$group': {
                        '_id': '$id', 
                        'latest': {
                            '$first': '$$ROOT'
                        }
                    }
                }, {
                    '$replaceRoot': {
                        'newRoot': '$latest'
                    }
                }, {
                    '$match': {
                        'active': True
                    }
                }
            ], 
            'as': 'nodes'
        }
    }, {
        '$lookup': {
            'from': 'relationship_versions', 
            'let': {
                'projectId': '$projectVersion.id', 
                'timestamp': '$timestamp'
            }, 
            'pipeline': [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {
                                    '$eq': [
                                        '$projectId', '$$projectId'
                                    ]
                                }, {
                                    '$lte': [
                                        '$lastModified', '$$timestamp'
                                    ]
                                }
                            ]
                        }
                    }
                }, {
                    '$sort': {
                        'lastModified': -1
                    }
                }, {
                    '$group': {
                        '_id': '$id', 
                        'latest': {
                            '$first': '$$ROOT'
                        }
                    }
                }, {
                    '$replaceRoot': {
                        'newRoot': '$latest'
                    }
                }, {
                    '$match': {
                        'active': True
                    }
                }
            ], 
            'as': 'relationships'
        }
    }, {
        '$addFields': {
            'projectVersion.tables': '$tables', 
            'projectVersion.nodes': '$nodes', 
            'projectVersion.relationships': '$relationships', 
            'projectVersion.lastChange': '$$ROOT'
        }
    }, {
        '$replaceRoot': {
            'newRoot': '$projectVersion'
        }
    }
    ]

    result = await async_db['change'].aggregate(pipeline).to_list(length=None)
    
    return result

async def get_projects_with_change(owner_id):
    pipeline = [
        {
            '$match': {
                'active': True,
                'owner.id': owner_id
            }
        },
        {
            '$lookup': {
                'from': 'change',
                'let': {'project_id': '$_id'},
                'pipeline': [
                    {'$match': {'$expr': {'$eq': ['$projectId', '$$project_id']}}},
                    {'$sort': {'timestamp': -1}},
                    {'$limit': 1},
                    {
                        '$project': {
                            'id': '$_id',
                            'timestamp': 1,
                            'name': 1,
                            'description': 1,
                            'dbTechnology': 1,
                            'projectType': 1,
                            'active': 1,
                            'owner': 1
                        }
                    }
                ],
                'as': 'lastChange'
            }
        },
        {
            '$addFields': {
                'lastChange': {'$arrayElemAt': ['$lastChange', 0]}
            }
        },
        {
            '$project': {
                '_id': 0,
                'id': '$_id',
                'name': 1,
                'description': 1,
                'dbTechnology': 1,
                'projectType': 1,
                'active': 1,
                'owner': 1,
                'lastChange': 1
            }
        }
    ]
    result = await async_db['project'].aggregate(pipeline).to_list(length=None)
    return result


def clean_openai_response(response):
    # Check if the response contains SQL
    if '```sql' in response and '```' in response.split('```sql')[1]:
        sql_content = response.split('```sql')[1].split('```')[0].strip()
        return sql_content, 'sql'

    # Check if the response contains JSON
    elif '```json' in response and '```' in response.split('```json')[1]:
        json_content = response.split('```json')[1].split('```')[0].strip()
        return json_content, 'json'
    elif response.startswith('{') and response.endswith('}'):
        return response.strip(), 'json'

    # If the format is unrecognized
    return response, 'unknown'

# Retrieve only the text between the markers ```json and ``` from OpenAI API responses
def extract_code_text(input_text, response_type):
    # Define a regular expression pattern to match text between ```json and ```
    pattern = r'```json(.*?)```'
    if response_type == ResponseType.SQL:
        pattern = r'```sql(.*?)```'

    # Use re.DOTALL to match across multiple lines
    match = re.search(pattern, input_text, re.DOTALL)
    
    if match:
        # Extract and return the matched text
        json_text = match.group(1).strip()
        return json_text
    else:
        return input_text

# Prompts OpenAI
def prompt_openai(model, system_message, user_message, response_type = ResponseType.JSON):
    client = OpenAI(api_key=get_settings().openai_key)
    print(system_message)
    print(user_message)
    try:
      response = client.chat.completions.create(
        model=model,
        messages=[
          {
            "role": "system",
            "content": system_message
          },
          {
            "role": "user",
            "content": user_message
          }
        ],
        temperature=0,
        max_tokens=2900,
        #top_p=0,
        frequency_penalty=0,
        presence_penalty=0,
        seed=0,
        #response_format={ "type": "json_object" }
      )
      #print(response.choices[0].message.content)
      # @TODO: Need to handle the situation where the code is not wrapped in json tags
      print(response.choices[0].message.content)
      result = extract_code_text(response.choices[0].message.content, response_type) 
      print(result)
      return result
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    

#Function to complete json project by adding active flag, project id and relationships
def complete_project(project_id, schema_json):

    # Dictionary to store primary key columns with their table IDs
    primary_keys = {}

    # First pass: Add unique IDs to tables and columns; identify primary keys
    for table in schema_json['tables']:
        table['id'] = generate()
        table['active'] = True
        table['projectId'] = project_id

        for column in table['columns']:
            column_id = generate()
            column['id'] = column_id
            column['active'] = True

            if column['primaryKey']:
                primary_key_name = (table['id'], column['name'])
                primary_keys[primary_key_name] = column_id

    # Second pass: Generate relationships
    relationships = []
    for table in schema_json['tables']:
        for column in table['columns']:
            column_key_name = (table['id'], column['name'])
            for primary_key_name, primary_key_id in primary_keys.items():
                if column_key_name != primary_key_name and column['name'] == primary_key_name[1]:
                    identifying = column['primaryKey']
                    relationships.append({
                        'id': generate(),
                        'parentColumn': primary_key_id,
                        'childColumn': column['id'],
                        'active': True,
                        'identifying': identifying,
                        'projectId': project_id
                    })

    # Add relationships to the schema
    schema_json['relationships'] = relationships

    return schema_json

# Generated nodes with corresponding positions using networkx
# Nodes will become more relevant when the concept of Diagrams are introduced
def generate_nodes(json_data, project_id):
    # Extract table IDs
    nodes = [table["id"] for table in json_data["tables"]]

    # Map column IDs to table IDs
    column_to_table = {}
    for table in json_data["tables"]:
        for column in table["columns"]:
            column_to_table[column["id"]] = table["id"]

    # Create edges based on relationships
    edges = []
    for relationship in json_data["relationships"]:
        parent_table = column_to_table[relationship["parentColumn"]]
        child_table = column_to_table[relationship["childColumn"]]
        edges.append((parent_table, child_table))

    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # Generate a basic layout
    pos = nx.kamada_kawai_layout(G=G, scale=750)

    # Generate a list of dictionaries with the specified structure
    table_positions = [
        {
            "id": generate(),  # Generate a unique ID using nanoid
            "tableId": key,
            "x": float(value[0]),  # Convert numpy float to Python float
            "y": float(value[1]),   # Convert numpy float to Python float
            "active": True,
            "projectId": project_id,
            "type": 'tableNode'
        }
        for key, value in pos.items()
    ]

    return table_positions

def generate_id_if_missing(json_array):
    for item in json_array:
        if "id" not in item:
            # Generate a unique ID using nanoid
            item["id"] = generate()

def complete_response_for_ai_tables(new_tables, existing_nodes, position):
    """
    Creates a graph representation in JSON format based on new and existing table data.

    This function takes two parameters: new_tables and existing_nodes. new_tables contains 
    information about new database tables and their relationships, while existing_nodes 
    contain details about already existing nodes and tables in a graph.

    The function generates a JSON object with two main elements: newNodes and newEdges.

    - newNodes: A list of nodes, each representing a new table. Each node is assigned a 
      unique identifier, an x and y coordinate (where y increases by 100 for each node), 
      and a data attribute containing the table information.

    - newEdges: A list of edges representing relationships. Each edge includes a data 
      attribute holding the corresponding relationship object with childColumn and parentColumn 
      attributes (using column IDs). It covers relationships within new tables and potential 
      relationships between existing tables and new tables. An edge is created if a primary 
      key column in an existing table matches by name with any column in the new tables. 
      Each edge has a source (the existing or parent node) and a target (the child node).

    Parameters:
    - new_tables (dict): A dictionary containing 'tables' and 'relationships' for new tables.
    - existing_nodes (dict): A dictionary containing 'nodes', 'tables', and 'relationships' 
      for existing elements in the graph.

    Returns:
    - dict: A dictionary with two keys 'newNodes' and 'newEdges', each containing a list of 
      nodes and edges respectively.
    """

    new_nodes = []
    new_edges = []
    y_position = position['y']
    x_position = position['x']

    # Create nodes for new tables
    for table in new_tables["tables"]:
        node = {
            "id": generate(),
            "position":{"x":x_position, "y":y_position},
            "data": table,
            "new": True,
            "type": 'tableNode'
        }
        new_nodes.append(node)
        y_position += 300 # TODO: Maybe multiple a factor by number of rows?

    # Mapping column ID to table node ID for new nodes
    column_to_node_id = {col["id"]: node["id"] for node in new_nodes for col in node["data"]["columns"]}

    # Mapping column ID to table ID
    column_to_table_id = {col["id"]: table["id"] for table in new_tables["tables"] for col in table["columns"]}


    # Create edges for relationships within new tables
    for relationship in new_tables["relationships"]:
        relationship["label"]: None
        parent_node_id = column_to_node_id.get(relationship["parentColumn"])
        child_node_id = column_to_node_id.get(relationship["childColumn"])
        if parent_node_id and child_node_id:
            new_edges.append({
                "id": relationship["id"],
                "active": True,
                "source": parent_node_id,
                "target": child_node_id,
                "type": 'floating',
                "markerEnd": 'endMarker',
                "markerStart": 'startMarker',
                "data": relationship
            })

    # Mapping primary key column names to their IDs in existing tables
    primary_key_name_to_id = {col["name"]: col["id"] for table in existing_nodes["tables"] for col in table["columns"] if col.get("primaryKey")}

    # Inspect new tables for potential new edges with existing tables
    for new_table in new_tables["tables"]:
        new_table_id = next(node["id"] for node in new_nodes if node["data"]["id"] == new_table["id"])
        for column in new_table["columns"]:
            primary_key_column_id = primary_key_name_to_id.get(column["name"])
            if primary_key_column_id:
                # Find the corresponding existing node
                for existing_node in existing_nodes["nodes"]:
                    existing_table_id = next((table["id"] for table in existing_nodes["tables"] if primary_key_column_id in [col["id"] for col in table["columns"]]), None)
                    if existing_table_id and existing_node["tableId"] == existing_table_id:
                        relationship = {
                            "id": generate(),
                            "active": True,
                            "identifying": False,
                            "parentColumn": primary_key_column_id,
                            "childColumn": column["id"],
                            "label": None
                        }
                        new_edges.append({
                            "id": relationship["id"],
                            "active": True,
                            "type": 'floating',
                            "source": existing_node["id"],
                            "target": new_table_id,
                            "data": relationship,
                            "markerEnd": 'endMarker',
                            "markerStart": 'startMarker'
                        })
    return {"newNodes": new_nodes, "newEdges": new_edges}