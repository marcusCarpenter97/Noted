from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser
import base64
import socket
import logging
from cryptography.hazmat.primitives import serialization

class ServiceListener:

    def __init__(self, device_id, transport_layer):
        self.device_id = device_id
        self.transport_layer = transport_layer

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)

        if not info:
            return

        properties = self.decode_dict(info.properties)

        if properties["device_id"] == self.device_id:
            return

        properties["peer_ip"] = socket.inet_ntoa(info.addresses[0])
        properties["peer_port"] = info.port
        properties["zeroconf_name"] = name

        self.transport_layer.register_new_peer(properties)

    def remove_service(self, zeroconf, service_type, name):
        logging.info(f"[-] Service removed: {name}")
        self.transport_layer.remove_service(name)

    def update_service(self, zeroconf, service_type, name):
        logging.info(f"[~] Service updated: {name}")

    def decode_dict(self, d):
        decoded = {}
        for k, v in d.items():
            key = k.decode() if isinstance(k, bytes) else k
            if key == "public_key":
                decoded[key] = base64.b64decode(v)
            else:
                decoded[key] = v.decode() if isinstance(v, bytes) else v
        return decoded

def get_default_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def advertise(device_id, public_key, device_name):
    zeroconf = Zeroconf()

    service_type = "_noted._tcp.local."
    service_name = f"{device_name}._noted._tcp.local."

    ip_address = socket.inet_aton(get_default_ip())
    port = 5000

    public_key_bytes = public_key.public_bytes(encoding=serialization.Encoding.DER,
                                               format=serialization.PublicFormat.SubjectPublicKeyInfo)

    public_key_b64 = base64.b64encode(public_key_bytes).decode("ascii")

    properties = {
        "device_id": device_id,
        "public_key": public_key_b64,
        "device_name": device_name
    }

    logging.info(f"Advertising with public key {public_key_b64}")

    info = ServiceInfo(
            type_=service_type,
            name=service_name,
            addresses=[ip_address],
            port=port,
            properties=properties)

    logging.info("Registering service...")
    zeroconf.register_service(info)

    return zeroconf, info

def discover(device_id, transport_layer):
    zeroconf = Zeroconf()
    listener = ServiceListener(device_id, transport_layer)

    service_type = "_noted._tcp.local."

    logging.info(f"Browsing for {service_type} ...")
    browser = ServiceBrowser(zeroconf, service_type, listener)

    return zeroconf

