import json
import re
import aiohttp
from nanoid import generate
from openai import OpenAI
from application.config import get_settings
import networkx as nx

# To be used for requests to ksql but it's global for performance reasons
session = aiohttp.ClientSession()

async def query_ksql(kdsqldb_cluster, ksql_query):
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
                return await response.json()
            else:
                print(f"Error querying ksqlDB: HTTP Status {response.status}")
                return []
    except Exception as e:
        print(f"Error querying ksqlDB: {e}")
        return []

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

# Retrieve only the text between the markers ```json and ``` from OpenAI API responses
def extract_json_text(input_text):
    # Define a regular expression pattern to match text between ```json and ```
    pattern = r'```json(.*?)```'
    
    # Use re.DOTALL to match across multiple lines
    match = re.search(pattern, input_text, re.DOTALL)
    
    if match:
        # Extract and return the matched text
        json_text = match.group(1).strip()
        return json_text
    else:
        return None

# Prompts OpenAI
def prompt_openai(model, system_message, user_message):
    client = OpenAI(api_key=get_settings.openai_key)

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
      print(system_message)
      print(user_message)
      print(response.choices[0].message.content)
      return extract_json_text(response.choices[0].message.content)
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
            "projectId": project_id
        }
        for key, value in pos.items()
    ]

    return table_positions