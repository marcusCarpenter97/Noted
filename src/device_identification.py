from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import uuid

class DeviceID:
    def __init__(self, db_worker):
        self.db_worker = db_worker

    def get_or_generate_device_id(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS device_id(uuid TEXT PRIMARY KEY)")
            cursor.execute("SELECT uuid FROM device_id")
            row = cursor.fetchone()

            if row:
                return row["uuid"]

            device_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO device_id (uuid) VALUES (?)", (device_id,))
            connection.commit()
            return device_id

        return self.db_worker.execute(_op, wait=True)

    def get_or_generate_public_private_keys(self):
        def _op(connection):
            cursor = connection.cursor()

            cursor.execute("""CREATE TABLE IF NOT EXISTS keys(
                            name TEXT PRIMARY KEY,
                            private_key BLOB,
                            public_key BLOB)""")

            cursor.execute("SELECT private_key, public_key FROM keys WHERE name='p2p'")
            row = cursor.fetchone()

            if row:
                private = serialization.load_der_private_key(row["private_key"], password=None)
                public = serialization.load_der_public_key(row["public_key"])
                return private, public

            private = ec.generate_private_key(ec.SECP256R1())
            public = private.public_key()

            private_bytes = private.private_bytes(encoding=serialization.Encoding.DER,
                                                  format=serialization.PrivateFormat.PKCS8,
                                                  encryption_algorithm=serialization.NoEncryption())

            public_bytes = public.public_bytes(encoding=serialization.Encoding.DER,
                                               format=serialization.PublicFormat.SubjectPublicKeyInfo)

            cursor.execute("INSERT INTO keys VALUES (?, ?, ?)", ("p2p", private_bytes, public_bytes))
            connection.commit()

            return private, public
        return self.db_worker.execute(_op, wait=True)

    def create_device_name_table(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS device_name(name TEXT PRIMARY KEY)")
            connection.commit()
        self.db_worker.execute(_op, wait=True)

    def store_device_name(self, device_name):
        def _op(connection, device_name):
            cursor = connection.cursor()
            cursor.execute("INSERT INTO device_name (name) VALUES (?)", (device_name,))
            connection.commit()
        self.db_worker.execute(_op, args=(device_name,), wait=True)

    def get_device_name(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM device_name")
            row = cursor.fetchone()

            if row:
                return row["name"]
            return None
        return self.db_worker.execute(_op, wait=True)
