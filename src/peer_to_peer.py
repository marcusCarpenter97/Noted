from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser
import socket
import time
import logging

class ServiceListener:

    def __init__(self, device_id):
        self.device_id = device_id

    def add_service(self, zeroconf, service_type, name):
        logging.info(f"[+] Service added: {name}")
        info = zeroconf.get_service_info(service_type, name)
        if info:
            properties = self.decode_dict(info.properties)
            if properties["device_id"] != self.device_id:
                print(" Address:", socket.inet_ntoa(info.addresses[0]))
                print(" Port:", info.port)
                print(" Conecting device id:", properties["device_id"])
                print(" New device connected:", properties["device_name"])

    def remove_service(self, zeroconf, service_type, name):
        logging.info(f"[-] Service removed: {name}")
        print(f"Device {name} disconected")

    def update_service(self, zeroconf, service_type, name):
        logging.info(f"[~] Service updated: {name}")

    def decode_dict(self, d):
        return {k.decode() if isinstance(k, bytes) else k:
                v.decode() if isinstance(v, bytes) else v
                for k, v in d.items()}


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

def advertise(device_id, device_name):
    zeroconf = Zeroconf()

    service_type = "_noted._tcp.local."
    service_name = f"{device_name}._noted._tcp.local."

    ip_address = socket.inet_aton(get_default_ip())
    port = 5000

    properties = {
        "device_id": device_id,
        "device_name": device_name
    }

    info = ServiceInfo(
            type_=service_type,
            name=service_name,
            addresses=[ip_address],
            port=port,
            properties=properties)

    logging.info("Registering service...")
    zeroconf.register_service(info)

    return zeroconf, info

def discover(device_id):
    zeroconf = Zeroconf()
    listener = ServiceListener(device_id)

    service_type = "_noted._tcp.local."

    logging.info(f"Browsing for {service_type} ...")
    browser = ServiceBrowser(zeroconf, service_type, listener)

    return zeroconf

