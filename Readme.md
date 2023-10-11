# Plankton - A MoF Chatbot

## Description
A chatbot that is able to parse `jsonl` files and responds to questions. The tech stack is as follows

- Flask: to create the api rest endpoints
- Mongo: for the databse
- Telegram: internal connection to the api
- Docker compose: to connect everything together
- NGINX: reroute flask to port 80

the flask endpoint will be visible at `http://localhost/`


## Installation

To get a local copy up and running, follow these steps:

1. Clone the repository
```bash
git clone <repository-link>
```

2. Navigate to the project directory
```bash
cd <project-directory>
```

3. Create .env file and add required environment variables
```bash
touch .env
# Open the .env file and add environment variables
```

4. Use Docker Compose to boot up services
```bash
docker-compose up
```

## Usage

To use the application, you can access the listed API endpoints from the base URL: ```http://localhost/```. Replace localhost with your server address if you're not testing locally.

### API Endpoints

1. Ask: `/ask`
2. Users: `/users`
3. Telegram: `/telegram/ask`
4. Review: `/review`

## Docker Compose services

The project uses Docker Compose to spin up the following services:

- `web`: an Nginx server that directs traffic to the backend
- `backend`: the main application server that handles client requests
- `telegram_bot`: a Telegram bot that sends and receives messages
- `mongo`: a MongoDB server for data persistence
- `mongo-express`: a web-based MongoDB admin interface

