from flask import Flask, request, jsonify
import logging
from plankton.data_processing import get_docs, split_documents
from plankton.embed_data import get_embeddings, embed_data
from plankton.conversational_agent import ChatbotManager
from pymongo import MongoClient
import os
from plankton.database import Database


# Set up logging with time
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# client = MongoClient("mongo:27017")


Database.initialize()


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    question = data.get("question", "Who is the minister of finance")

    docs = None

    # Embed all docs and get vectorstore
    logger.info("Embedding documents")
    embed = get_embeddings()
    logger.info("Creating vectorstore from embeddings")

    vectorstore = embed_data(docs=docs, embedding=embed)

    chatbotManager = ChatbotManager(vectorstore)
    agent = chatbotManager.initialize_agent()
    logger.info(f'Agent question: "{question}"')
    response = agent(question)

    Database.insert("query", {"question": question, "response": response})

    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.environ.get("FLASK_SERVER_PORT", 9090), debug=True)
