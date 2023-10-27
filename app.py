from functools import wraps
import datetime
import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restful import Api, Resource, abort

from plankton.conversational_agent import ChatbotManager
from plankton.database import Database
from plankton.embed_data import embed_data, get_embeddings

app = Flask(__name__)

# Set up logging with time
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up rate limiting for API requests
limiter = Limiter(
    app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)

api = Api(app)

# Define the path to the .env file
dotenv_path = os.path.join(".env")

# Load the .env file
load_dotenv(dotenv_path)

# Initialize the database
Database.initialize()


def token_required(f):
    """
    Decorator function to require an API token for certain routes
    """

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


def transform_id(user):
    """
    Helper function to transform the '_id' field of a user object to a string
    """
    if "_id" in user:
        user["_id"] = str(user["_id"])


class Ask(Resource):
    """
    Flask-RESTful resource for handling POST requests to the /ask endpoint
    """

    @token_required
    def post(self):
        """
        Handle POST requests to the /ask endpoint
        """
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

        # Inserting data into the database
        Database.insert("query", insert_data)

        return jsonify(response)


class Users(Resource):
    """
    Flask-RESTful resource for handling GET and POST requests to the /users endpoint
    """

    @token_required
    def get(self):
        """
        Handle GET requests to the /users endpoint
        """
        users = Database.find("users", {})
        for user in users:
            transform_id(user)

        return jsonify(list(users))

    @token_required
    def post(self):
        """
        Handle POST requests to the /users endpoint
        """
        data = request.get_json(force=True)
        if "user_id" not in data:
            abort(400, message="User ID is missing in the request body")

        user_id = data.get("user_id")
        user = Database.find_one("users", {"user_id": user_id})
        if user:
            abort(400, message=f"User with ID {user_id} already exists")

        Database.insert("users", data)

        return jsonify({"message": "User created successfully"}), 201


class Telegram(Resource):
    """
    Flask-RESTful resource for handling POST requests to the /telegram/ask endpoint
    """

    @limiter.limit("10 per minute")
    @token_required
    def post(self):
        """
        Handle POST requests to the /telegram/ask endpoint
        """
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


class Review(Resource):
    @token_required
    class Review(Resource):
        """
        A class to handle review creation for users.

        ...

        Methods
        -------
        post()
            Creates a review for a user.

        """

        def post(self):
            """
            Creates a review for a user.

            Returns
            -------
            json
                A JSON object containing a success message.

            Raises
            ------
            HTTPException
                If required fields are missing or if the sentiment is not 'positive' or 'negative'.

            Examples
            --------
            To create a review for a user, send a POST request to the endpoint with the following data:
            {
                "user_id": "123",
                "sentiment": "positive",
                "remarks": "Great experience with the product!"
            }

            The response will be a JSON object with a success message:
            {
                "message": "Review created successfully"
            }
            """

            data = request.get_json(force=True)

            required_fields = [
                "user_id",
                "sentiment",
            ]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                logger.info(f"Missing fields: {missing_fields}")
                abort(
                    400,
                    message=f"These fields are missing in the request body: {', '.join(missing_fields)}",
                )

            user_id = data.get("user_id")

            # on telegram create user if not in database
            if user_id not in [user["user_id"] for user in Database.find("users", {})]:
                required_fields = [
                    "chat_id",
                    "user_id",
                    "user_name",
                    "first_name",
                    "last_name",
                ]

                missing_fields = [
                    field for field in required_fields if field not in data
                ]

                if missing_fields:
                    logger.info(f"Missing fields: {missing_fields}")
                    abort(
                        400,
                        message=f"These fields are missing in the request body: {', '.join(missing_fields)}",
                    )

                Database.insert(
                    "users",
                    {
                        "chat_id": data.get("chat_id"),
                        "user_id": data.get("user_id"),
                        "user_name": data.get("user_name"),
                        "first_name": data.get("first_name"),
                        "last_name": data.get("last_name"),
                    },
                )

                logger.info(f"User with ID {user_id} created successfully")

            user = Database.find_one("users", {"user_id": user_id})
            if user is None:
                abort(400, message=f"User with ID {user_id} does not exist")

            sentiment = data.get("sentiment")
            if sentiment not in ["positive", "negative"]:
                abort(400, message=f"Sentiment must be either 'positive' or 'negative'")

            insert_data = {
                "user_id": user_id,
                "sentiment": sentiment,
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "remarks": data.get("remarks") or "",
            }

            Database.insert("review", insert_data)
            logger.info(f"Review for user with ID {user_id} created successfully")

            return jsonify({"message": "Review created successfully"})


# Add the Flask-RESTful resources to the API
api.add_resource(Ask, "/ask")
api.add_resource(Users, "/users")
api.add_resource(Telegram, "/telegram/ask")
api.add_resource(Review, "/review")

if __name__ == "__main__":
    # Start the Flask app
    app.run(host="0.0.0.0", port=os.environ.get("FLASK_SERVER_PORT", 9090), debug=True)
