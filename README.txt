Install ollama on Windows from here: https://ollama.com/download

# Check if its working with the version command.
ollama --version

# If not you may need to set your path.

# Install the model.
ollama pull nomic-embed-text

# To run the Docker images run the command:

docker compose build
docker compose run --rm advertiser
docker compose run --rm listener

# This will run in CLI mode.
