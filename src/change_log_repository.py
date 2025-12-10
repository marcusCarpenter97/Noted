import uuid
import json

class ChangeLog:

    def __init__(self, db):
        self.db = db

    def create_change_log_table(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS change_log (
                            op_id TEXT PRIMARY KEY,
                            note_id TEXT,
                            operation_type TEXT,
                            timestamp DATETIME,
                            device_id TEXT,
                            payload TEXT)""")
        self.db.commit_to_database()

    def log_operation(self, note_id, operation_type, payload):

        payload.pop("embeddings", None)

        cursor = self.db.get_database_cursor()
        op_id = str(uuid.uuid4())
        device_id = self.db.get_or_create_peer_id()

        cursor.execute("""
                INSERT INTO change_log (op_id, note_id, operation_type, timestamp, device_id, payload)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)""",
                (op_id, note_id, operation_type, device_id, json.dumps(payload)))
        self.db.commit_to_database()
