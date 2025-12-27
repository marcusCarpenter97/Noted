## Install ollama from here: https://ollama.com/download

## Check if it's working with the version command.
ollama --version

## If not and you are on Windows, you may need to set your path.
To add ollama to your path press Win+r and search for sysdm.cpl, navigate to
the advanced tab and click on environment variables at the bottom. Select Path
in system variables and click edit. Select New and insert the following path
(or wherever it was installed):

C:\Users\<YOUR USERNAME>\AppData\Local\Programs\Ollama

## Run the app in the background or start the Ollama server
ollama serve

## Install the model.
ollama pull nomic-embed-text

## To run the Docker images run the commands:

docker compose build
docker compose run --rm advertiser
docker compose run --rm listener

### This will run in CLI mode.
Note: the installer is still work in progress, at the moment is checks whether
requirements are met, but installation of ollama and the model need to be
manual.
