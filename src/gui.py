import sys
from PySide6.QtWidgets import (QApplication, QTextEdit, QWidget, QVBoxLayout,
                               QLineEdit, QPushButton, QHBoxLayout, QFrame,
                               QLabel, QScrollArea)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, Qt

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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noted desktop")
        self.setGeometry(50, 50, 800, 600)
        self.setWindowIcon(QIcon("assets/noted-logo.png"))
        
        main_layout = QHBoxLayout()
        search_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        # Left pannel
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search for a note...")

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_for_note)

        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_button)

        self.text_box = QTextEdit()

        left_layout.addLayout(search_layout)
        left_layout.addWidget(self.text_box)

        # Right pannel
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
        self.text_box.setPlainText(result.get("contents", ""))

    def search_for_note(self):
        print("Searching for note...")

        # TODO Fake results (replace with your real search output)
        results = [
                {"title": "Meeting Notes", "contents": "Full note A", "tags": "one, two, three"},
                {"title": "Ideas", "contents": "Full note B", "tags": "some,tags"},
                {"title": "My note", "contents": "Full note C", "tags": "notag"},
                {"title": "A very long note", "contents": "Full note DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD", "tags": "DDDD"},
        ]

        self.clear_results()

        for result in results:
            card = ResultCard(result)
            card.clicked.connect(self.on_result_clicked)
            self.results_layout.insertWidget(
                self.results_layout.count() - 1, card
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
