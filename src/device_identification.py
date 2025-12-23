from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import uuid

class DeviceID:
    def __init__(self, db):
        self.db = db

    def get_or_generate_device_id(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS device_id(uuid TEXT PRIMARY KEY)")

        cursor.execute("SELECT uuid FROM device_id")
        row = cursor.fetchone()

        if row:
            return row[0]

        device_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO device_id (uuid) VALUES (?)", (device_id,))
        self.db.commit_to_database()

        return device_id

    def get_or_generate_public_private_keys(self):
        cursor = self.db.get_database_cursor()

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
        self.db.commit_to_database()

        return private, public
