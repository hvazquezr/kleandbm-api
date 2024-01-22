import json
import re
import requests
import base64
import io
import aiohttp
from nanoid import generate
from openai import OpenAI
from application.config import get_settings
import networkx as nx
from enum import Enum
from PIL import Image

class ResponseType(str, Enum):
    JSON = "json"
    SQL = "sql"

# To be used for requests to ksql but it's global for performance reasons
session = aiohttp.ClientSession()

# Formats replies from ksql in a more intuitive json format   
def process_ksql_response(json_data):
    # Extract the schema from the first element
    schema_str = re.sub(r'<.*?>', '', json_data[0]['header']['schema'])
    # Split the schema into individual columns and extract names
    column_names = [col.split()[0].strip('`') for col in schema_str.split(',')]

    # Process each row
    result = []
    for item in json_data[1:]:
        row_data = item['row']['columns']
        # Map column names to row values
        row_dict = dict(zip(column_names, row_data))
        result.append(row_dict)
    return result

async def async_query_ksql(kdsqldb_cluster, ksql_query):
    headers = {
        'Content-Type': 'application/vnd.ksql.v1+json; charset=utf-8',
        'Accept': 'application/json'
    }
    data = json.dumps({
        'ksql': ksql_query,
        'streamsProperties': {}
    })

    try:
        # Use the provided session to make the HTTP request
        async with session.post(kdsqldb_cluster + '/query', headers=headers, data=data, ssl=False) as response:
            if response.status == 200:
                return process_ksql_response(await response.json())
            else:
                print(f"Error querying ksqlDB: HTTP Status {response.status}")
                return []
    except Exception as e:
        print(f"Error querying ksqlDB: {e}")
        return []
    
def query_ksql(kdsqldb_cluster, ksql_query):
    headers = {
        'Content-Type': 'application/vnd.ksql.v1+json; charset=utf-8',
        'Accept': 'application/json'
    }
    data = json.dumps({
        'ksql': ksql_query,
        'streamsProperties': {}
    })

    try:
        query_response = requests.post(kdsqldb_cluster+'/query', headers=headers, data=data)
        return process_ksql_response(query_response.json())
    except Exception as e:
        print(f"Error querying ksqlDB: {e}")
        return []

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
        return None

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
      result = extract_code_text(response.choices[0].message.content, response_type) 
      print(result)
      return result
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    

def process_b64_json_to_image(b64_json_data, path, id):

    # Decode the base64 data to get the binary data of the image
    image_data = base64.b64decode(b64_json_data)

    # Read the image data into PIL
    image = Image.open(io.BytesIO(image_data))

    # Resize the image
    resized_image = image.resize((302, 302))

    # Save or re-encode as needed
    # For instance, saving to a file
    resized_image.save(f"{path}{id}.png")
    

def generate_image(project_id, prompt):
    client = OpenAI(api_key=get_settings().openai_key)
    response = client.images.generate(
    model="dall-e-3",
    prompt=prompt,
    size="1024x1024",
    quality="standard",
    n=1,
    response_format="b64_json",
    style="natural"
    )

    b64_json_output = response.data[0].b64_json

    process_b64_json_to_image(b64_json_output, "project_images/", project_id)

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
            "projectId": project_id
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
            "new": True
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