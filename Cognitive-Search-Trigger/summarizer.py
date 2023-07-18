import logging
import time

import mlflow
from langchain import OpenAI, PromptTemplate
from langchain.chains.summarize import load_summarize_chain
import openai


MYLOGGERNAME = "AZSearchSummarization"




class Summarizer():
    """A class used to summarize documents.

    Attributes:
        logger: Instance of logger used for logging.
        connection_param_dict: Dictionary of connection parameters.
        model_params: Dictionary of model parameters.
        prompts: Dictionary of prompts for summarization.

    Methods:
        _load_chain: Load the summarization chain based on chain type.
        _prepare_prompt: Prepare the prompt template.
        _select_chain_type: Select the appropriate chain type.
        summarize: Summarize the given documents.
        _log_metrics: Log metrics and tags for MLFlow.
    
    """


    # TODO: Optimize the class calls
    def __init__(self, connection_params, model_config):
        """
        Constructs all the necessary attributes for the Summarizer object.

        Args:
            connection_params (dict): User parameter dict required for Azure connections.
            model_config (dict): Model parameter dict for embedding options & deployment engine for Azure.
        """
        self.logger = logging.getLogger(MYLOGGERNAME)
        self.connection_param_dict = connection_params
        self.model_params = model_config["summarize_contexts"]["model_params"]
        self.prompts = model_config["summarize_contexts"]["prompts"]
        self.set_connection_params()

    def set_connection_params(self):
        """
        Set the Azure's OpenAI API connection parameters.

        Parameters
        ----------
        self : GPTModelCall
            An instance of the GPTModelCall class.

        Raises
        ------
        KeyError
            If the 'platform' key is not found in the connection_param_dict dictionary.

        Returns
        -------
        None
        """
        try:
            if self.connection_param_dict["platform"] == "azure":
                print("Setting the Azure OpenAI connection parameters")
                openai.api_type = self.connection_param_dict["api_type"]
                openai.api_base = self.connection_param_dict["api_base"]
                openai.api_version = self.connection_param_dict["api_version"]
        except KeyError as e:
            raise KeyError(
                f"""An error occurred during the setting the connection parameters.
                                The error message is: {e}."""
            )

    def _select_prompt(self, query, chain_type):
        """Select Prompt Based on the chains"""

        summarize_prompt = self.prompts["system_role"] + self.prompts["summarize_prompt"] + self.prompts["guidelines"]
        summarize_prompt = self._prepare_prompt(query, summarize_prompt, ["text"])

        combine_prompt = None
        refine_prompt = None
        if chain_type == "map_reduce":
            combine_prompt = self._prepare_prompt(query, self.prompts["combine_prompt_template"], ["text"])

        elif chain_type == "stuff":
            pass

        elif chain_type == "refine":
            # refine_prompt = PromptTemplate(input_variables=["existing_answer", "text"], template=self.prompts["refine_prompt_template"])
            refine_prompt = self._prepare_prompt(query, self.prompts["refine_prompt_template"], ["existing_answer", "text"])

        else:
            raise ValueError("Incorrect chain type")

        return summarize_prompt, combine_prompt, refine_prompt

    def _load_chain(self, query, chain_type):
        """
        Helper method to load summarization chain based on chain type.

        Args:
            query (str): The query to be searched in the documents.
            chain_type (str): The type of chain to be used.

        Returns:
            object: The summarization chain object.
        """
        temperature = self.model_params["temperature"]
        engine = self.model_params["engine"]
        llm = OpenAI(temperature=temperature, engine=engine)

        summarize_prompt, combine_prompt, refine_prompt = self._select_prompt(query, chain_type)
        chain = self._select_chain_type(chain_type, llm, summarize_prompt, combine_prompt, refine_prompt)
        return chain

    @staticmethod
    def _prepare_prompt(query, template, input_variables):
        """
        Prepare the prompt template.

        Args:
            query (str): The query to be searched in the documents.
            template (str): The prompt template to be used for summarization.
            input_variables (list): List of input variables.

        Returns:
            object: The prepared prompt template.
        """
        return PromptTemplate(template=template.replace("<user_query>", query), input_variables=input_variables)

    @staticmethod
    def _select_chain_type(chain_type, llm, summarize_prompt, combine_prompt=None, refine_prompt=None):
        """
        Select the appropriate chain type.

        Args:
            chain_type (str): The type of chain to be used.
            llm (OpenAI): OpenAI instance with temperature and engine parameters.
            summarize_prompt (str): The summarize prompt template.
            combine_prompt (str): The combine prompt template.
            refine_prompt (str): The refine prompt template.

        Returns:
            object: The summarization chain object based on the given chain type.

        Raises:
            ValueError: If the chain type is not one of "map_reduce", "stuff", or "refine".
        """
        if chain_type == "map_reduce":
            return load_summarize_chain(llm, map_prompt=summarize_prompt, combine_prompt=combine_prompt, chain_type=chain_type)

        elif chain_type == "stuff":
            return load_summarize_chain(llm, prompt=summarize_prompt, chain_type=chain_type)

        elif chain_type == "refine":
            # print(summarize_prompt.template)
            # print(refine_prompt.template)

            return load_summarize_chain(llm, question_prompt=summarize_prompt, refine_prompt=refine_prompt, chain_type=chain_type)
        else:
            raise ValueError("Incorrect chain type")

    def summarize(self, query, top_k_retrieved_docs):
        """
        Perform summarization on the retrieved documents.

        Args:
            query (str): The query to be searched in the documents.
            top_k_retrieved_docs (list): The top k retrieved documents.

        Returns:
            str: The generated summary.
        """
        chain = self._load_chain(query, self.model_params["chain_type"])

        start_summarization = time.time()
        summary = chain.run(top_k_retrieved_docs)
        end_summarization = time.time() - start_summarization

        self._log_metrics(self.prompts["summarize_prompt"], summary, chain, end_summarization)
        return summary

    def _log_metrics(self, prompt_template, summary, chain, duration):
        """
        Log metrics and tags for MLFlow.

        Args:
            prompt_template (str): The used prompt template.
            summary (str): The generated summary.
            chain (object): The chain used for summarization.
            duration (float): Time taken for summarization.
        """
        mlflow.log_params(self.model_params)
        mlflow.set_tags({"engine": self.model_params["engine"], "prompt template": prompt_template, "length of summary": len(summary)})

        mlflow.langchain.log_model(chain, "load summarize chain")
        mlflow.set_tag("summary", summary)
        mlflow.log_text(summary, "summary.txt")
        mlflow.log_metric("summarization duration", duration)
        mlflow.log_metric("no. characters summarization", len(summary))
        mlflow.log_metric("no. words summarization", len(summary.split(" ")))
