import base64
import logging
import threading
from nacl.public import Box
from dataclasses import dataclass
from nacl.public import PublicKey, PrivateKey

@dataclass
class PeerInfo:
    device_id: str
    device_name: str
    ip_address: str
    port: int

class TransportLayer:
    def __init__(self, private_key):
        self.peers = []
        self.boxes = dict()
        self.private_key = private_key

    def register_new_peer(self, peer_data):
        print(" Connecting device id:", peer_data["device_id"])
        print(" New device connected:", peer_data["device_name"])
        print(f" New connection from: {peer_data['peer_ip']}:{peer_data['peer_port']}")

        peer = PeerInfo(device_id=peer_data["device_id"], device_name=peer_data["device_name"], ip_address=peer_data["peer_ip"], port=peer_data["peer_port"])

        for p in self.peers:
            if p.device_id == peer_data["device_id"]:
                logging.warning(f"Peer {peer_data['device_id']} already connected")
                return

        self.peers.append(peer)
        private = PrivateKey(self.private_key)
        public = PublicKey(base64.b64decode(peer_data["public_key"]))
        self.boxes[peer_data["device_id"]] = Box(private, public)

    def _server_loop(self):
        print("TCP thread established.")

    def run_tcp_server(self):
        server_thread = threading.Thread(target=self._server_loop, args=())
        server_thread.start()
        server_thread.join()