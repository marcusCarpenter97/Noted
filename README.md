# Noted: an offline-first AI powered note taking app

Noted enables you to take simple text based notes. It prioritises offline
usage but it can also share notes between devices using a peer to peer
network. Moreover, its search engine is powered by AI, more precisely the BM25
algorithm combined with an embedding model.

## Main features:
Offline note taking, peer to peer synchronisation (nothing gets stored in a
server), communication is end-to-end encrypted, smart search using a
combination of embeddings and BM25.

Disclaimer: even though these features work reasonably well this project is
very much an alpha version and I plan on leaving it at that. It is important
also to note that even though this project is very focussed on privacy (no
server, encryption) it is by no means production ready.

## Architecture overview
- PySide6 GUI
- SQLite local storage
- Change log + Lamport clocks
- Zeroconf discovery + encrypted TCP sync
- Hybrid search (BM25 + embeddings via FAISS)

## Requirements

Use Python 3.14.2 or above.

This project has one dependency which needs to be installed separately as the
installer is still work in progress. To run properly you'll need to install
Ollama on your device.

You can install ollama from here: https://ollama.com/download

And check if it's working using the command:

`ollama --version`

If not and you are on Windows, you may need to set your path. To add Ollama to
your path press Win+r and search for sysdm.cpl, navigate to the advanced tab
and click on environment variables at the bottom. Select Path in system
variables and click edit. Select New and insert the following path (or
wherever it was installed):

`C:\Users\<YOUR USERNAME>\AppData\Local\Programs\Ollama`

Once installed, run the app in the background or start the Ollama server
using:

`ollama serve`

Don`t forget to install the model:

`ollama pull nomic-embed-text`

## Running the app

An executable should be packaged in with the project and available
[here](https://github.com/marcusCarpenter97/Noted/releases/download/1.1.0/Noted.exe).

However, it is possible to run the GUI version by calling:

`python src/gui.py`

And the CLI version (mainly used for testing) by calling:

`python src/cli.py`

**Remember to make sure Ollama is running.**

Running the app will create a log file called noted and a folder called
database in the same directory as from where you ran the executable.

Also keep in mind that the CLI does not have proper sync features, it will
attempt to synchronize with every device found without proper authentication.
This can lead to malicious behaviour, i.e. a malicious actor with a version of
the app can take all your notes. Moreover, the CLI version does not remember
device names, forcing the user to type it in each time it logs in.

## For developers

If you are interested in contributing to the project or tinkering with it
yourself, you can start by testing it via Docker or the unit tests. The unit
tests run with pytest. To run the test container you'll need Docker. There are
two containers, an advertiser and a listener. This is from the time where I
was testing Zeroconf and I still used a client (advertiser) and server
(listener). Of course, now, the app acts as both. Docker is used here to
simulate multiple clients in a network enabling the testing of the peer to
peer synchronization.

To run the Docker images run the commands:

`docker compose build`

`docker compose run --rm advertiser`

`docker compose run --rm listener`

Note: this will run in CLI mode.

To compile the Python code into an executable use he following command:

`pyinstaller --onefile --icon="assets/noted-logo.ico" src/gui.py`
