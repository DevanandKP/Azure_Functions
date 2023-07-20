import logging
import requests
import json
import os
import mlflow
import time
import logging
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from langchain.docstore.document import Document

from .summarizer import Summarizer

connection_params = {'platform': 'azure',
 'api_type': 'azure',
 'api_base': 'https://nlp-search-open-ai.openai.azure.com/',
 'api_version': '2023-03-15-preview',
 'api_keyVaultName': 'nlpSearchKeyVault',
 'api_secretName': 'az-openapi-key-1',
 'user_email': 'harsh.tiwari@tigeranalytics.com',
 '_ipython_canary_method_should_not_exist_': {}}

model_config = {'summarize_contexts': {'model_params': {'engine': 'gpt-35-turbo-deploy',
   'temperature': 0,
   'max_tokens': None,
   'n': 1,
   'stop': None,
   'function': 'ChatCompletion',
   'timeout': 15,
   'max_tries': 3,
   'chain_type': 'refine'},
  'prompts': {'system_role': 'You are an expert in giving executive summaries to business audience.',
   'summarize_prompt': "\nGiven below text, summarize to a business audience to answer the following question \n\nQuestions: '<user_query>':.\n\nText:\n '{text}'",
   'additional_context': None,
   'guidelines': '\n\nFollow the below mentioned guidelines while generating response: \nGuideline 1: Use bulleted list for each points in the summary. \nGuideline 2: summary should contain one or two sentences. \nGuideline 3: summary should be provided based on factual data.',
   'refine_prompt_template': "Your job is to produce a final summary. \nWe have provided an existing summary up to a certain point: '{existing_answer}'. \nWe have the opportunity to refine the existing summary (only if needed) with some more context below.\n------------\n'{text}'\n------------\n Given the new context, refine the original summary for the following question \n\nQuestions: '<user_query>'. If the context isn't useful, return the original summary.",
   'combine_prompt_template': "Given below text, summarize to a business audience to answer the following question \n\nQuestions: '<user_query>'.\n\nText:\n'{text}'"}}}

obj = Summarizer(connection_params,model_config)

azure_SEARCH_SERVICE_NAME = os.environ["CUSTOMCONNSTR_azure_SEARCH_SERVICE_NAME"]
azure_SEARCH_API_KEY = os.environ["CUSTOMCONNSTR_azure_SEARCH_API_KEY"]
azure_SEARCH_INDEX_NAME = "demo-index"
function_access_key = os.environ["CUSTOMCONNSTR_function_access_key"]

cog_search_endpoint = f"https://{azure_SEARCH_SERVICE_NAME}.search.windows.net/"
api_version = '?api-version=2020-06-30'
headers = {'Content-Type': 'application/json',
        'api-key': azure_SEARCH_API_KEY }
indexer_name = "ppt-pdf-new"

def list_docs(output):
    content=[]
    for i in range(len(output['value'])):
        content.append(output['value'][i]['content'])
    return content



def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    start_time=time.time()

    query_params = req.params
    search_query = query_params.get('query')
    #key_query = query_params.get('key')
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
        end_time1 =time.time()
        print("time to get query", end_time1-start_time)

        searchstring = f'&search={search_query}&$top=2'
        url = cog_search_endpoint + f"indexes/{azure_SEARCH_INDEX_NAME}/docs" + api_version + searchstring
        response  = requests.get(url, headers=headers, json=searchstring)
        output = response.json()

        end_time2 =time.time()
        print("time to get cognitive search response", end_time2-end_time1)

        #output_json=json.dumps(output,indent =2) 

        summary = list_docs(output)

        docs = [Document(page_content=t) for t in summary[:3]]
        
        end_time3 =time.time()
        print("time for pre-processing", end_time3-end_time2)
        
        final_summary= obj.summarize(search_query,docs)

        end_time4 =time.time()
        print("time for summary", end_time4-end_time3)

        response_data = {
        "json_data": output,
        #"my_list": summary,
        "final_summary":final_summary}

        response_json = json.dumps(response_data,indent=4)

        end_time5 =time.time()
        print("time to get function response", end_time5-end_time4)

        return func.HttpResponse(response_json,mimetype="application/json",status_code=200)

        #return func.HttpResponse(body=output_json,status_code=200)
    else:
        return func.HttpResponse(
            "Pass a keyword in the query string or in the request body to get results.",
            status_code=200
        )
        
    #except Exception as e:
        #logging.error(str(0))
        #return func.HttpResponse(f"An error occured while processsing the request,{str(0)}", status_code=500)