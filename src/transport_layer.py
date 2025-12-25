import os
import base64
import socket
import pickle
import logging
import threading
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

@dataclass
class PeerInfo:
    device_id: str
    device_name: str
    ip_address: str
    port: int
    zeroconf_name: str

class TransportLayer:
    def __init__(self, device_id, public_key, private_key):
        self.peers = []
        self.device_id = device_id
        self.public_key = public_key
        self.private_key = private_key
        self.message_handlers = []
        self.peers_public_keys = dict()  # Maps peer's device ids to their public keys.
        self.service_name_to_device_id = dict()  # This keeps track of peer names for removal.
        self.shared_secrets = dict()  # Maps peer device id to a shared secret.
        self.symetric_keys = dict()  # Maps peer device id to symetric keys.

    def register_new_peer(self, peer_data):

        # TODO Is it possible to place all of these attributes in an object searcheable by device_id?
        new_peer = PeerInfo(device_id=peer_data["device_id"], device_name=peer_data["device_name"],
                            ip_address=peer_data["peer_ip"], port=peer_data["peer_port"],
                            zeroconf_name=peer_data["zeroconf_name"])

        for p in self.peers:
            if p.device_id == new_peer.device_id:
                logging.warning(f"Peer {new_peer.device_id} already connected")
                return

        pk = peer_data["public_key"]

        self.peers.append(new_peer)
        self.service_name_to_device_id[peer_data["zeroconf_name"]] = peer_data["device_id"]
        self.peers_public_keys[peer_data["device_id"]] = peer_data["public_key"]
        peer_public_key = serialization.load_der_public_key(peer_data["public_key"])
        self.shared_secrets[peer_data["device_id"]] = self.private_key.exchange(ec.ECDH(), peer_public_key)
        self.symetric_keys[peer_data["device_id"]] = HKDF(algorithm=hashes.SHA256(),
                                                          length=32,
                                                          salt=None,
                                                          info=b"session").derive(self.shared_secrets[peer_data["device_id"]])

    def remove_service(self, service_name):
        peer_id_to_remove = self.service_name_to_device_id.pop(service_name, None)
        if peer_id_to_remove is None:
            logging.warning("Removing unregistered device with name %s", service_name)
            return
        self.peers = [peer for peer in self.peers if peer.device_id != peer_id_to_remove]
        logging.info("Removed %s from peers.", peer_id_to_remove)

    def get_peers(self):
        return self.peers

    def push_changes(self, changes_to_push):
        results = []

        for peer in self.peers:
            try:
                # We use a handshake to identify the peer on the other end.
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((peer.ip_address, peer.port))
                handshake = {"device_id": self.device_id}
                handshake_bytes = pickle.dumps(handshake)
                sock.sendall(len(handshake_bytes).to_bytes(4, "big"))
                sock.sendall(handshake_bytes)

                changes = [dict(row) for row in changes_to_push]
                plaintext = pickle.dumps(changes)

                iv = os.urandom(12)
                encryptor = Cipher(algorithms.AES(self.symetric_keys[peer.device_id]), modes.GCM(iv)).encryptor()
                ciphertext = encryptor.update(plaintext) + encryptor.finalize()
                tag = encryptor.tag

                sock.sendall(len(ciphertext).to_bytes(4, "big"))
                sock.sendall(ciphertext)

                sock.sendall(len(iv).to_bytes(4, "big"))
                sock.sendall(iv)

                sock.sendall(len(tag).to_bytes(4, "big"))
                sock.sendall(tag)

                # Send EOF to the server to ensure connection is closed.
                sock.sendall((0).to_bytes(4, "big"))

                results.append({"peer": peer.device_id, "status": "ok", "count": len(changes_to_push)})

            except Exception as e:
                logging.error(f"Error pushing changes to peer {peer.device_id}: {e}")
                results.append({"peer": peer.device_id, "status": "error"})
        return results

    def register_message_handler(self, handler):
        self.message_handlers.append(handler)

    def _handle_message(self, device_id, message):
        for handler in self.message_handlers:
            handler(device_id, message)

    def recv_exact(self, sock, n):
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("EOF")
            data += chunk
        return data

    def _handle_client(self, sock, address):

        try:
            length = int.from_bytes(self.recv_exact(sock, 4), "big")
            raw_data = self.recv_exact(sock, length)
            handshake = pickle.loads(raw_data)

            device_id = handshake["device_id"]

            # Check if device is known.
            if device_id not in self.peers_public_keys:
                logging.warning("Received handshake from unknown device. Exiting...")
                return

            while True:
                length = int.from_bytes(self.recv_exact(sock, 4), "big")
                encrypted = self.recv_exact(sock, length)

                length = int.from_bytes(self.recv_exact(sock, 4), "big")
                iv = self.recv_exact(sock, length)

                length = int.from_bytes(self.recv_exact(sock, 4), "big")
                tag = self.recv_exact(sock, length)

                eof = int.from_bytes(self.recv_exact(sock, 4), "big")

                if not encrypted:
                    break

                decryptor = Cipher(algorithms.AES(self.symetric_keys[device_id]),
                                   modes.GCM(iv, tag)).decryptor()
                plaintext = decryptor.update(encrypted) + decryptor.finalize()

                message = pickle.loads(plaintext)

                self._handle_message(device_id, message)

                # Closes server after message is sent.
                if eof == 0:
                    break

        except Exception as e:
            logging.error(f"Error handling peer {address}: {e}")
        finally:
            sock.close()

    def _server_loop(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('', 5000))  # Accept connection from any IP on port 5000.
        server_socket.listen()
        logging.info("TCP server listening on port 5000.")

        while True:
            client_socket, client_address = server_socket.accept()
            logging.info(f"New TCP connection from {client_address}")
            handle = threading.Thread(target=self._handle_client, args=(client_socket, client_address), daemon=True)
            handle.start()

    def run_tcp_server(self):
        server_thread = threading.Thread(target=self._server_loop, args=(), daemon=True)
        server_thread.start()
