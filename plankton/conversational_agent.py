from langchain.agents import Tool
from langchain.chat_models import ChatOpenAI
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.chains import RetrievalQA
from langchain.retrievers.multi_query import MultiQueryRetriever
from dotenv import load_dotenv
import os
from langchain.agents import initialize_agent
import logging

# Define the base path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the path to the .env file
dotenv_path = os.path.join(BASE_DIR, ".env")

# Load the .env file
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set up logging with time
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """
        You are a chatbot trained on the United arab emirates ministry of finance website.
        """


class ChatbotManager:
    def __init__(self, vectorstore):
        # Initialize properties
        self.model_name = "gpt-4"
        self.temperature = 0.0
        self.openai_api_key = OPENAI_API_KEY
        self.request_timeout = 30
        self.max_retries = 12
        self.search_type = "mmr"
        self.search_kwargs = {"k": 3}
        self.parser_key = "lines"
        self.tool_name = "MoF Knowledgebase"
        self.tool_description = (
            "A chatbot trained on all the information on the "
            "MoF website including PDFs"
        )
        self.vectorstore = vectorstore
        self.agent_verbose = True
        self.agent_max_iterations = 3

    def initialize_agent(self):
        self.llm = self._initialize_llm()

        # Initialize retriever, memory and retrieval qa chain
        self.retriever_from_llm = self._initialize_retriever_from_llm()
        self.conversational_memory = self._initialize_conversational_memory()
        self.qa_tool = self._initialize_retrieval_qa_tool()
        self.agent = self._initialize_agent()
        return self.agent

    def _initialize_llm(self):
        return ChatOpenAI(
            openai_api_key=self.openai_api_key,
            model_name=self.model_name,
            temperature=self.temperature,
            request_timeout=self.request_timeout,
            max_retries=self.max_retries,
        )

    def _initialize_retriever_from_llm(self):
        return MultiQueryRetriever.from_llm(
            retriever=self.vectorstore.as_retriever(
                search_type=self.search_type, search_kwargs=self.search_kwargs
            ),
            llm=self.llm,
            parser_key=self.parser_key,
        )

    def _initialize_conversational_memory(self):
        return ConversationBufferWindowMemory(
            memory_key="chat_history", k=3, return_messages=True
        )

    def _initialize_retrieval_qa_tool(self):
        qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever_from_llm,
            verbose=True,
        )

        return Tool(
            name=self.tool_name,
            func=qa.run,
            description=self.tool_description,
        )

    def _initialize_agent(self):
        return initialize_agent(
            agent="chat-conversational-react-description",
            tools=[self.qa_tool],
            llm=self.llm,
            verbose=self.agent_verbose,
            max_iterations=self.agent_max_iterations,
            agent_kwargs={"system_message": SYSTEM_MESSAGE},
            early_stopping_method="generate",
            memory=self.conversational_memory,
        )
