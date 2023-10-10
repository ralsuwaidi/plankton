from flask import Flask, request, jsonify
import logging
from plankton.embed_data import get_embeddings, embed_data
from plankton.conversational_agent import ChatbotManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from plankton.database import Database
from functools import wraps
from dotenv import load_dotenv


# Set up logging with time
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

limiter = Limiter(
    app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)

# Define the path to the .env file
dotenv_path = os.path.join(".env")

# Load the .env file
load_dotenv(dotenv_path)


Database.initialize()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "X-API-KEY" in request.headers:
            token = request.headers["X-API-KEY"]
        if not token or token != os.getenv("API_SECRET_TOKEN"):
            return (
                jsonify(
                    {
                        "message": "Token is missing or invalid, add a token as a 'X_API_KEY' header"
                    }
                ),
                403,
            )

        return f(*args, **kwargs)

    return decorated


@app.route("/ask", methods=["POST"])
@limiter.limit("5 per minute")
@token_required
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
