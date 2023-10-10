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
from flask_restful import Resource, Api, abort
import datetime

# Set up logging with time
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

limiter = Limiter(
    app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)

api = Api(app)

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
            abort(
                403,
                message="Token is missing or invalid, add a token as a 'X_API_KEY' header",
            )

        return f(*args, **kwargs)

    return decorated


class Ask(Resource):
    @limiter.limit("10 per minute")
    @token_required
    def post(self):
        data = request.get_json(force=True)
        if "question" not in data:
            abort(400, message="Question is missing in the request body")

        if "user_id" not in data:
            abort(400, message="User ID is missing in the request body")

        user_id = data.get("user_id")
        question = data.get("question")

        user = Database.find("users", {"user_id": user_id})
        if len(list(user)) == 0:
            abort(400, message=f"User with ID {user_id} does not exist")

        embed = get_embeddings()

        vectorstore = embed_data(docs=None, embedding=embed)

        chatbotManager = ChatbotManager(vectorstore)
        agent = chatbotManager.initialize_agent()
        logger.info(f'Agent question: "{question}"')
        response = agent(question)

        # Preparing data for insertion
        insert_data = {
            "question": question,
            "response": response,
            "user_id": user_id,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        Database.insert("query", insert_data)

        return jsonify(response)


class Users(Resource):
    @token_required
    def get(self):
        users = Database.find("users", {})
        return jsonify(list(users))

    @token_required
    def post(self):
        data = request.get_json(force=True)
        if "user_id" not in data:
            abort(400, message="User ID is missing in the request body")

        user_id = data.get("user_id")
        user = Database.find_one("users", {"user_id": user_id})
        if user:
            abort(400, message=f"User with ID {user_id} already exists")

        Database.insert("users", data)

        return jsonify(data)


class Telegram(Resource):
    @limiter.limit("10 per minute")
    @token_required
    def post(self):
        data = request.get_json(force=True)

        required_fields = [
            "question",
            "chat_id",
            "user_id",
            "user_name",
            "first_name",
            "last_name",
        ]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            abort(
                400,
                message=f"These fields are missing in the request body: {', '.join(missing_fields)}",
            )

        question = data.get("question")
        embed = get_embeddings()

        vectorstore = embed_data(docs=None, embedding=embed)
        chatbotManager = ChatbotManager(vectorstore)
        agent = chatbotManager.initialize_agent()

        logger.info(f'Agent question: "{question}"')
        response = agent(question)

        # Preparing data for insertion
        insert_data = {
            "question": question,
            "response": response,
            "chat_id": data.get("chat_id"),
            "user_id": data.get("user_id"),
            "user_name": data.get("user_name"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
        }

        # Inserting data into the database
        Database.insert("query", insert_data)

        return jsonify(response)


api.add_resource(Ask, "/ask")
api.add_resource(Users, "/users")
api.add_resource(Telegram, "/telegram/ask")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.environ.get("FLASK_SERVER_PORT", 9090), debug=True)
