import logging
import requests
import json

import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

azure_SEARCH_SERVICE_NAME = "nlp-cognitive-search"
azure_SEARCH_API_KEY = "rFcoeiOpi95CRLX2oWJnu36sNSN9vtfj8i3BGerNKtAzSeBmb8Om"
azure_SEARCH_INDEX_NAME = "ppt-pdf-new"

cog_search_endpoint = f"https://{azure_SEARCH_SERVICE_NAME}.search.windows.net/"
api_version = '?api-version=2020-06-30'
headers = {'Content-Type': 'application/json',
        'api-key': azure_SEARCH_API_KEY }
indexer_name = "ppt-pdf-new"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    search_query = req.params.get('query')
    if not search_query:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            search_query = req_body.get('query')

    if search_query:
        searchstring = f'&search={search_query}&$top=3'
        url = cog_search_endpoint + "indexes/ppt-pdf-new/docs" + api_version + searchstring
        response  = requests.get(url, headers=headers, json=searchstring)
        output = response.json()
        output=json.dumps(output) 
        return func.HttpResponse(body=output)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
