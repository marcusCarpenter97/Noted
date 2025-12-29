import sys
import pickle
import logging
import traceback
from functools import partial
from PySide6.QtWidgets import (QApplication, QTextEdit, QWidget, QVBoxLayout,
                               QLineEdit, QPushButton, QHBoxLayout, QFrame,
                               QLabel, QScrollArea, QInputDialog, QMessageBox,
                               QSystemTrayIcon, QDialog)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, Qt

from faiss_engine import Faiss
from tokenizer import Tokenizer
from note_index import NoteIndex
from database_worker import DBWorker
from sync_manager import SyncManager
from lamport_clock import LamportClock
from search_engine import SearchEngine
from lexical_index import LexicalIndex
from installation_wizard import run_wizard
from device_identification import DeviceID
from transport_layer import TransportLayer
from change_log_repository import ChangeLog
from notes_repository import NotesRepository
from peer_to_peer import advertise, discover
from embedding_provider import EmbeddingProvider

class ResultCard(QFrame):
    clicked = Signal(dict)

    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.result = result

        self.setObjectName("ResultCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        title = QLabel(result.get("title", "Untitled"))
        title.setStyleSheet("font-weight: bold; font-size: 14px;")

        contents = QLabel(result.get("contents", ""))
        contents.setStyleSheet("color: #666;")

        tags = QLabel(result.get("tags", ""))

        layout.addWidget(title)
        layout.addWidget(contents)
        layout.addWidget(tags)

        self.setStyleSheet("""
            QFrame#ResultCard {
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 8px;
                background: white;
                }
            QFrame#ResltCard:hover {
                background: #f2f2f2;
                }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.result)

class ResultsPanel(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWidgetResizable(True)

        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(8, 8, 8, 8)

        self.setWidget(self.container)

        self.layout.addStretch()
        
    def clear_results(self):
        while self.layout.count() > 1:
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def add_result(self, results: list[dict]):
        self.clear_results()

        for result in results:
            card = ResultCard(result)
            card.clicked.connect(self.on_card_clicked)
            self.layout.insertWidget(self.layout.count() - 1, card)

    def on_card_clicked(self, result: dict):
        print("Clicked:", result)

class ConfirmPeerDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Accept peer?")
        self.setModal(True)
        self.setFixedSize(300, 150)

        layout = QVBoxLayout()

        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        accept_button = QPushButton("Accept")
        accept_button.clicked.connect(self.accept)
        layout.addWidget(accept_button)

        reject_button = QPushButton("Reject")
        reject_button.clicked.connect(self.reject)
        layout.addWidget(reject_button)

        self.setLayout(layout)

class MainWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Noted desktop")
        self.setGeometry(50, 50, 800, 600)
        self.setWindowIcon(QIcon("assets/noted-logo.png"))
        
        self.current_note_id = ""

        self.app.transport_layer.peer_discovered.connect(self.on_peer_discovered)

        main_layout = QHBoxLayout()
        search_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        title_layout = QHBoxLayout()
        contents_layout = QVBoxLayout()
        tags_layout = QHBoxLayout()
        buttons_layout = QHBoxLayout()

        # Left panel
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search for a note...")

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_for_note)

        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_button)

        self.title_label = QLabel("Note`s title:")
        self.title_field = QLineEdit()

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.title_field)

        self.contents_label = QLabel("Note`s contents:")
        self.contents_field = QTextEdit()

        contents_layout.addWidget(self.contents_label)
        contents_layout.addWidget(self.contents_field)

        self.tags_label = QLabel("Note`s tags:")
        self.tags_field = QLineEdit()

        tags_layout.addWidget(self.tags_label)
        tags_layout.addWidget(self.tags_field)

        self.insert_button = QPushButton("Insert new")
        self.edit_button = QPushButton("Save edits")
        self.delete_button = QPushButton("Delete note")
        self.sync_button = QPushButton("Sync devices")

        self.insert_button.clicked.connect(self.insert_a_note)
        self.edit_button.clicked.connect(self.edit_a_note)
        self.delete_button.clicked.connect(self.delete_a_note)
        self.sync_button.clicked.connect(self.sync)

        buttons_layout.addWidget(self.insert_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.sync_button)

        left_layout.addLayout(search_layout)
        left_layout.addLayout(title_layout)
        left_layout.addLayout(contents_layout)
        left_layout.addLayout(tags_layout)
        left_layout.addLayout(buttons_layout)

        # Right panel
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.addStretch()

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setWidget(self.results_container)

        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addWidget(self.results_scroll, stretch=2)

        self.setLayout(main_layout)

    def clear_results(self):
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def on_result_clicked(self, result: dict):
        self.current_note_id = result.get("uuid")
        self.title_field.setText(result.get("title", ""))
        self.contents_field.setPlainText(result.get("contents", ""))
        self.tags_field.setText(result.get("tags", ""))

    def search_for_note(self):

        user_query = self.search_bar.text().strip()

        # Searching with an empty string crashes the programme in the
        # faiss engine (maybe only on an empty database).
        if user_query == "":
            return

        top_results = self.app.search_engine.hybrid_search(user_query)

        if top_results is None:
            QMessageBox.warning(self, "Could not search!", "The database appears to be empty.")
            return

        if len(top_results) == 0:
            QMessageBox.warning(self, "Could not search!", "No search results found.")
            return

        self.clear_results()

        for result in top_results:
            note = self.app.notes_db.get_note(result[0])
            note = dict(note)  # SQLite to dict.
            card = ResultCard(note)
            card.clicked.connect(self.on_result_clicked)
            self.results_layout.insertWidget(
                self.results_layout.count() - 1, card
            )

    def insert_a_note(self):
        title = self.title_field.text().strip()
        contents = self.contents_field.toPlainText().strip()
        tags = self.tags_field.text().strip()

        responce = self.app.embedding_prov.embed(f"{title} {contents} {tags}")
        embeddings = pickle.dumps(responce['embedding'])

        note_id = self.app.notes_db.create_note(title, contents, embeddings, tags)

        self.app.search_engine.index_note(note_id)
        self.app.lexical_index.index_note_for_lexical_search(note_id, title, contents)
        self.app.faiss_engine.add_embedding(note_id, responce['embedding'])

        # Convert the SQLite row object into a dictionary.
        note_as_dict = dict(self.app.notes_db.get_note(note_id))

        self.app.lamport_clock.increment_lamport_time()
        self.app.lamport_clock.save_lamport_time_to_db()
        self.app.change_log.log_operation(note_id, "create", note_as_dict, self.app.lamport_clock.now(), self.app.device_id)

        self.app.synchronization_manager.sync()

        QMessageBox.information(self, "Note created!", "You created a new note.")

        self.title_field.clear()
        self.contents_field.clear()
        self.tags_field.clear()

    def delete_a_note(self):
        # No note selected, do nothing.
        if self.current_note_id == "":
            return
        self.app.notes_db.mark_note_as_deleted(self.current_note_id)
        self.app.lexical_index.delete_note_from_lexical_search(self.current_note_id)
        self.app.search_engine.remove_from_index(self.current_note_id)
        self.app.faiss_engine.delete_embedding(self.current_note_id)
        self.app.lamport_clock.increment_lamport_time()
        self.app.lamport_clock.save_lamport_time_to_db()
        self.app.change_log.log_operation(self.current_note_id, "delete", {"deleted": 1}, self.app.lamport_clock.now(), self.app.device_id)
        self.app.synchronization_manager.sync()
        QMessageBox.information(self, "Note deleted!", "You deleted a note.")

        self.title_field.clear()
        self.contents_field.clear()
        self.tags_field.clear()

        self.clear_results()

    def edit_a_note(self):
        # No note selected, do nothing.
        if self.current_note_id == "":
            return

        title = self.title_field.text().strip()
        contents = self.contents_field.toPlainText().strip()
        tags = self.tags_field.text().strip()

        old_note = self.app.notes_db.get_note(self.current_note_id)

        change_as_json = {}
        # Build the change log with only what's changed.
        if title is not None:
            change_as_json['title'] = title
        if contents is not None:
            change_as_json['contents'] = contents
        if tags is not None:
            change_as_json['tags'] = tags

        # Build the note merging old and new contents.
        if title is None:
            title = old_note['title']
        if contents is None:
            contents = old_note['contents']
        if tags is None:
            tags = old_note['tags']

        responce = self.app.embedding_prov.embed(f"{title} {contents} {tags}")
        embeddings = pickle.dumps(responce['embedding'])

        self.app.notes_db.update_note(self.current_note_id, title, contents, embeddings, tags)
        self.app.lexical_index.index_note_for_lexical_search(self.current_note_id, title, contents)
        self.app.search_engine.update_index(self.current_note_id)

        self.app.faiss_engine.update_embedding(self.current_note_id, responce['embedding'])

        change_as_json['embeddings'] = embeddings
        self.app.lamport_clock.increment_lamport_time()
        self.app.lamport_clock.save_lamport_time_to_db()
        self.app.change_log.log_operation(self.current_note_id, "update", change_as_json, self.app.lamport_clock.now(), self.app.device_id)

        self.app.synchronization_manager.sync()

        QMessageBox.information(self, "Note edited!", "You edited a note.")

    def sync(self):
        self.app.synchronization_manager.sync()

    def confirm_peer(self, peer_data):
        self.peer_dialog = ConfirmPeerDialog(f"Accept new connection from peer with name: {peer_data['zeroconf_name']}?", parent=self)
        return self.peer_dialog.exec() == QDialog.Accepted

    def on_peer_discovered(self, peer_data):
        if self.confirm_peer(peer_data):
            self.app.transport_layer.register_new_peer(peer_data)
            logging.info("User accepted peer %s", peer_data["device_id"])
        else:
            logging.info("User rejected peer %s", peer_data["device_id"])

class App:
    def __init__(self):
        self.db_worker = DBWorker()
        self.device = DeviceID(self.db_worker)

        self.device.create_device_name_table()
        self.device_id = self.device.get_or_generate_device_id()
        self.private_key, self.public_key = self.device.get_or_generate_public_private_keys()

        self.device_name = self.device.get_device_name()
        if self.device_name is None:
            text, ok_pressed = QInputDialog.getText(
                None,
                "First time seeing device!",
                "Please enter a name for your device:"
            )
            if ok_pressed and text.strip():
                self.device.store_device_name(text.strip())
                self.device_name = text.strip()

        self.transport_layer = TransportLayer(self.device_id, self.public_key, self.private_key)
        self.transport_layer.run_tcp_server()

        self.advertiser, self.info = advertise(self.device_id, self.public_key, self.device_name)
        self.discoverer = discover(self.device_id, self.transport_layer)

        self.embedding_prov = EmbeddingProvider()

        self.lamport_clock = LamportClock(self.db_worker)
        self.lamport_clock.initialize_lamport_clock()

        self.notes_db = NotesRepository(self.db_worker)
        self.notes_db.create_notes_table()

        self.note_index = NoteIndex(self.db_worker)
        self.note_index.create_word_index_table()

        self.lexical_index = LexicalIndex(self.db_worker)
        self.lexical_index.create_lexical_table()

        self.change_log = ChangeLog(self.db_worker, self.device_id)
        self.change_log.create_change_log_table()

        self.faiss_engine = Faiss(self.embedding_prov, self.notes_db)

        self.tokenizer = Tokenizer()

        self.search_engine = SearchEngine(self.notes_db, self.note_index,
                                          self.lexical_index,
                                          self.faiss_engine,
                                          self.embedding_prov, self.tokenizer)

        self.synchronization_manager = SyncManager(self.db_worker,
                                                   self.device_id,
                                                   self.notes_db,
                                                   self.change_log,
                                                   self.lamport_clock,
                                                   self.search_engine,
                                                   self.lexical_index,
                                                   self.faiss_engine,
                                                   self.embedding_prov,
                                                   self.transport_layer)

        self.synchronization_manager.create_last_sync_table()
        self.synchronization_manager.initialize_sync_table()
        self.synchronization_manager.create_lamport_last_sync_table()

def exception_hook(exc_type, exc_value, exc_traceback):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Application Error")
    msg.setText("An unexpected error occurred:")
    msg.setDetailedText(tb_str)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()
    sys.exit(1)

def shutdown(app):
    logging.info("Shutting down app...")
    app.db_worker.shutdown()
    # TODO send logout signal to peers.
    app.advertiser.unregister_service(app.info)
    app.advertiser.close()
    app.discoverer.close()

if __name__ == "__main__":

    logging.basicConfig(handlers=[logging.FileHandler("noted.log")],
                        level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    logging.captureWarnings(True)

    qt_app = QApplication(sys.argv)

    sys.excepthook = exception_hook

    if not run_wizard():
        sys.exit(0)

    app = App()

    window = MainWindow(app)
    window.show()

    qt_app.aboutToQuit.connect(partial(shutdown, app))
    sys.exit(qt_app.exec())
