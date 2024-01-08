import requests
import json

from application.config import get_settings

settings = get_settings()

async def query_ksql(ksql_query):
    headers = {
        'Content-Type': 'application/vnd.ksql.v1+json; charset=utf-8',
        'Accept': 'application/json'
    }
    data = json.dumps({
        'ksql': ksql_query,
        'streamsProperties': {}
    })

    try:
        # With Authentication
        #response = requests.post(KSQLDB_CONFIG['cluster']+'/query', headers=headers, data=data, auth=(KSQLDB_CONFIG['key'], KSQLDB_CONFIG['secret']))

        # No Authentication
        response = requests.post(settings.kdsqldb_cluster+'/query', headers=headers, data=data)
        return response.json()
    except Exception as e:
        print(f"Error querying ksqlDB: {e}")
        return []