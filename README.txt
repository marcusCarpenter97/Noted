Install ollama on Windows from here: https://ollama.com/download

# Check if it's working with the version command.
ollama --version

# If not, you may need to set your path.

# Start the Ollama service (or run the app in the background)
ollama serve

# Install the model.
ollama pull nomic-embed-text

# To run the Docker images run the command:

docker compose up --build
docker attach noted-advertiser-1
docket attach noted-listener-1
#docker compose run --rm advertiser
#docker compose run --rm listener

# This will run in CLI mode.
