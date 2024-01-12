import json
import re
import aiohttp
from openai import OpenAI

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
def prompt_openai(openai_key, model, system_message, user_message):
    client = OpenAI(api_key=openai_key)

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