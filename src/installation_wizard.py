import os
import platform
import tempfile
import subprocess
import urllib.request
import requests
import traceback
import logging
from installation_wizard_cli import download_installer, run_installer, is_ollama_runnig, is_model_downloaded, OLLAMA_HOST, OLLAMA_INSTALLER_URL

if platform.system() == "Windows":
    import winreg

    UNINSTALL_KEYS = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

if os.getenv("RUNNING_IN_DOCKER", 0) == 0:
    from PySide6.QtCore import QThread, Signal
    from PySide6.QtWidgets import QDialog, QLabel, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout


def find_install_location(root, key_path):
    try:
        with winreg.OpenKey(root, key_path) as key:
            return winreg.QueryValueEx(key, "InstallLocation")[0]
    except FileNotFoundError:
        return None

class CheckWorker(QThread):
    finished = Signal(bool, str)

    def run(self):
        try:
            ok, log = check_environment()
            self.finished.emit(ok, log)
        except Exception:
            tb = traceback.format_exc()
            logging.error(tb)
            self.finished.emit(False, tb)

class InstallationWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Noted setup")
        self.setModal(True)
        self.resize(500, 300)

        self.status_label = QLabel("Checking system requirements...")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.retry_btn = QPushButton("Retry")
        self.exit_btn = QPushButton("Exit")
        self.install_btn = QPushButton("Install missing components")

        self.retry_btn.clicked.connect(self.run_checks)
        self.exit_btn.clicked.connect(self.reject)
        self.install_btn.clicked.connect(self.install)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_view)
        layout.addWidget(self.install_btn)

        btns = QHBoxLayout()
        btns.addWidget(self.retry_btn)
        btns.addWidget(self.exit_btn)
        layout.addLayout(btns)

        self.run_checks()

    def run_checks(self):
        self.status_label.setText("Checking Ollama and models...")
        self.worker = CheckWorker()
        self.worker.finished.connect(self.on_check_finished)
        self.worker.start()

    def reject(self):
        super().reject()

    def install(self):
        if platform.system() == "Windows":
            self.log_view.append("Installing Ollama for Windows...")
            windows_installer()
        else:
            self.log_view.append("Installing Ollama for Linux...")
            linux_installer()

    def on_check_finished(self, ok, log):
        self.log_view.append(log)
        if ok:
            self.accept()
        else:
            self.status_label.setText("Missing requirements detected.")

def run_wizard(parent=None) -> bool:
    dialog = InstallationWizard(parent)
    return dialog.exec() == QDialog.Accepted

def check_environment():
    if not is_ollama_runnig():
        return False, "Ollama not installed or not running"
    if not is_model_downloaded("nomic-embed-text"):
        return False, "Model missing"
    return True, "Environment OK"

def windows_installer():
    with tempfile.TemporaryDirectory() as tmp:
        installer = os.path.join(tmp, "OllamaSetup.exe")
        download_installer(installer)
        run_installer(installer)

        path = find_install_location(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Ollama")
        add_to_user_path(path)
        print(path)
        # TODO run app in background.
    return False, "Installing for Windows."

def linux_installer():
    return False, "Installing for Linux."

def add_to_user_path(new_dir):
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Environment",
        0,
        winreg.KEY_READ | winreg.KEY_WRITE
    ) as key:
        try:
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""

        paths = current_path.split(";")
        if new_dir not in paths:
            updated_path = current_path + (";" if current_path else "") + new_dir
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, updated_path)
