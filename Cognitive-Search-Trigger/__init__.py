import logging
import requests
import json
import os

import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

#from summarizer import Summarizer

azure_SEARCH_SERVICE_NAME = os.environ["CUSTOMCONNSTR_azure_SEARCH_SERVICE_NAME"]
azure_SEARCH_API_KEY = os.environ["CUSTOMCONNSTR_azure_SEARCH_API_KEY"]
azure_SEARCH_INDEX_NAME = "ppt-pdf-new"
function_access_key = os.environ["CUSTOMCONNSTR_function_access_key"]

cog_search_endpoint = f"https://{azure_SEARCH_SERVICE_NAME}.search.windows.net/"
api_version = '?api-version=2020-06-30'
headers = {'Content-Type': 'application/json',
        'api-key': azure_SEARCH_API_KEY }
indexer_name = "ppt-pdf-new"



def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    query_params = req.params
    search_query = query_params.get('query')
    key_query = query_params.get('key')
    #no_of_docs = query_params.get('nos')

    '''
    if key_query != function_access_key:
        return func.HttpResponse("Unauthorized Access! Enter the correct access key", status_code=401)
    else:
    '''
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
        output=json.dumps(output,indent =2) 
        return func.HttpResponse(body=output,status_code=200)
    else:
        return func.HttpResponse(
            "Pass a keyword in the query string or in the request body to get results.",
            status_code=200
        )
        
    #except Exception as e:
        #logging.error(str(0))
        #return func.HttpResponse(f"An error occured while processsing the request,{str(0)}", status_code=500)