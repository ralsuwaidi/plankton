import logging
import click
import os
from plankton.data_processing import get_docs, split_documents
from plankton.embed_data import get_embeddings, embed_data
from plankton.conversational_agent import ChatbotManager

# Set up logging with time
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--data-dir", default="./data/clean_dump", help="Directory of the data.")
@click.option(
    "--delete-existing-db",
    is_flag=True,
    default=False,
    help="Whether to delete the existing database or not.",
)
@click.option(
    "--question",
    default="Who is the minister of finance",
    help="Question to ask the agent.",
)
def main(data_dir, delete_existing_db, question):
    docs = None
    # Only fetch and chop docs if the data_dir doesn't exist or delete_existing_db is True
    if not os.path.exists(data_dir) or delete_existing_db:
        # Get docs from source
        logger.info("Getting documents from source")
        docs = get_docs(data_dir)
        # Chop docs
        logger.info("Splitting documents")
        docs = split_documents(docs)

    # Embed all docs and get vectorstore
    logger.info("Embedding documents")
    embed = get_embeddings()
    logger.info("Creating vectorstore from embeddings")
    vectorstore = embed_data(
        docs=docs, embedding=embed, delete_existing_db=delete_existing_db
    )

    chatbotManager = ChatbotManager(vectorstore)
    agent = chatbotManager.initialize_agent()
    logger.info(f'Agent question: "{question}"')
    response = agent(question)
    logger.info(f"Agent response: {response['output']}")


if __name__ == "__main__":
    main()
