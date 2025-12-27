import os
import platform
import tempfile
import subprocess
import urllib.request
import requests
import traceback
import logging

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"

def run_wizard_cli():
    if not is_ollama_runnig():
        download = input("Ollama is not runnig. Dow you want to download it? Yes/No\n")
        if download == "Yes":
            if platform.system() == "Windows":
                with tempfile.TemporaryDirectory() as tmp:
                    installer = os.path.join(tmp, "OllamaSetup.exe")
                    download_installer(installer)
                    run_installer(installer)
            else:
                curl_output = subprocess.run(["curl", "-fsSL", "https://ollama.com/install.sh"], capture_output=True, check=True)
                subprocess.run(["sh"], input=curl_output.stdout)
        else:
            raise RuntimeError("Ollama is required to run. You can download it from: https://ollama.com/download")
    if not is_model_downloaded("nomic-embed-text"):
        download = input("The model seems to be missing. Do you want to download it? Yes/No\n")
        if download == "Yes":
            pull_model()
        else:
            raise RuntimeError("An Ollama model is required to run. Use the ollama pull commad to download a model.")
    
def download_installer(destination):
    with requests.get(OLLAMA_INSTALLER_URL, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def run_installer(installer_path):
    logging.info("Rnning installer.")
    subprocess.run([installer_path, "/S"], check=True)

def pull_model(model_name="nomic-embed-text"):
    print(f"Pulling model: {model_name}")
    subprocess.run([f"ollama pull {model_name}"], shell=True, check=True)
    print("Model ready!")

def is_ollama_runnig():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/version", timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False

def is_model_downloaded(model_name: str) -> bool:
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        r.raise_for_status()
        models = r.json().get("models", [])
        return any(m["name"].startswith(model_name) for m in models)
    except requests.RequestException:
        return False
