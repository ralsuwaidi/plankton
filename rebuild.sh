docker run --rm plankton-backend python main.py --delete-existing-db
docker compose down
docker compose up -d --build