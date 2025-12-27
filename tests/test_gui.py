
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from gui import MainWindow

@pytest.fixture
def peer_data():
    return {
        "device_id": "peer-123",
        "device_name": "Peer Laptop",
        "zeroconf_name": "Peer Laptop._noted._tcp.local.",
        "peer_ip": "127.0.0.1",
        "peer_port": 5000,
        "public_key": b"fake-key",
    }

@pytest.fixture
def main_window(qapp):
    app = FakeApp()
    window = MainWindow(app)
    return window

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

class FakeTransportLayer(QObject):
    peer_discovered = Signal(dict)

    def __init__(self):
        super().__init__()

    def register_new_peer(self, peer_data):
        pass

class FakeApp:
    def __init__(self):
        self.transport_layer = FakeTransportLayer()

def test_peer_accepted_registers_peer(mocker, main_window, peer_data):
    # Arrange
    mocker.patch.object(main_window, "confirm_peer", return_value=True)

    spy = mocker.spy(
        main_window.app.transport_layer,
        "register_new_peer"
    )

    # Act
    main_window.on_peer_discovered(peer_data)

    # Assert
    spy.assert_called_once_with(peer_data)

def test_peer_rejected_does_not_register_peer(mocker, main_window, peer_data):
    # Arrange
    mocker.patch.object(main_window, "confirm_peer", return_value=False)

    spy = mocker.spy(
        main_window.app.transport_layer,
        "register_new_peer"
    )

    # Act
    main_window.on_peer_discovered(peer_data)

    # Assert
    spy.assert_not_called()

