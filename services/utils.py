import json
import re
import aiohttp

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
        async with session.post(kdsqldb_cluster + '/query', headers=headers, data=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error querying ksqlDB: HTTP Status {response.status}")
                return []
    except Exception as e:
        print(f"Error querying ksqlDB: {e}")
        return []

    
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