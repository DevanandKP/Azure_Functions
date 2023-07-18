import logging
import os
import azure.functions as func
import json
import time
from requests import get, post
import requests
from urllib.parse import quote

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.search.documents.aio import SearchClient


form_endpoint = os.environ["CUSTOMCONNSTR_form_endpoint"]
key = os.environ["CUSTOMCONNSTR_key"]
conn_str = os.environ["CUSTOMCONNSTR_conn_str"]


input_container = "formrec-ip-openai-poc"
#input_blob = os.path.join("/azure function - form recognizer- cognitive search", "input")
output_container = "openai-poc"
blob_service_client = BlobServiceClient.from_connection_string(conn_str)


azure_SEARCH_SERVICE_NAME = os.environ["CUSTOMCONNSTR_azure_SEARCH_SERVICE_NAME"]
azure_SEARCH_API_KEY = os.environ["CUSTOMCONNSTR_azure_SEARCH_API_KEY"]
azure_SEARCH_INDEX_NAME = os.environ["CUSTOMCONNSTR_azure_SEARCH_INDEX_NAME"]

cog_search_endpoint = f"https://{azure_SEARCH_SERVICE_NAME}.search.windows.net/"
api_version = '?api-version=2020-06-30'
headers = {'Content-Type': 'application/json',
        'api-key': azure_SEARCH_API_KEY }
indexer_name = "formrec-indexer"

result_in_dict1 = {}


def double_to_integer(data):
    if isinstance(data,dict):
        return {key:double_to_integer(value) for key, value in data.items()}

    elif isinstance(data,list):
        return [double_to_integer(element) for element in data]

    elif isinstance(data, float):
        return int(data)

    else:
        return data
    
def extract_url_content(data,url):
    blob_url = quote(url, safe=':/')
    response = {}
    response["url"]=blob_url
    response["content"] = data["content"]
    return response


async def analyze_document(blob_url,name):
    document_analysis_client = DocumentAnalysisClient(endpoint=form_endpoint, credential=AzureKeyCredential(key))
    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-document", blob_url)
    #wait_sec = 10 #???
    #time.sleep(wait_sec)
    result = poller.result()
    result_in_dict = result.to_dict()

    '''
    blob_url = quote(blob_url, safe=':/')
    result_in_dict1["url"]=blob_url
    result_in_dict1["content"] = result_in_dict["content"]
    '''
    result_in_dict1 = extract_url_content(result_in_dict,blob_url)
    response = double_to_integer(result_in_dict1)
    resp_json = json.dumps(response)


    #blob_name = f"op_{count}.json"
    blob_name = f"{name}.json"
    container_client = blob_service_client.get_container_client(output_container)
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(resp_json, overwrite=True)



async def main(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Name: {myblob.name}\n"
                 f"Blob Size: {myblob.length} bytes")
    
    
    container_client = blob_service_client.get_container_client(input_container)
    count = 0
    for blob in container_client.list_blobs():
    #for blob in container_client.walk_blobs(name_starts_with=input_blob):
        blob_url = container_client.url + "/" + str(blob.name)
        logging.info(f"blob url {blob_url}")
        #count += 1
        name = os.path.splitext(blob.name)[0]
        await analyze_document(blob_url,name)
    
    indexer_endpoint = f"{cog_search_endpoint}indexers/{indexer_name}/run{api_version}"
    indexer_response = requests.post(url = indexer_endpoint,headers = headers)
    logging.info(f"indexer response {indexer_response}")

    searchstring = '&search=data&$top=1'
    url = cog_search_endpoint + "indexes/formrec-index/docs" + api_version + searchstring
    response  = requests.get(url, headers=headers, json=searchstring)
    query = response.json()

    with open("op_cogsearch.json", "w") as json_file:
        json.dump(query,json_file,indent =2)