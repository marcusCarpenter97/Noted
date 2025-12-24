import uuid
import json

class ChangeLog:

    def __init__(self, db_worker):
        self.db_worker = db_worker

    def create_change_log_table(self):
        def _op(connection):
            cursor = self.db.get_database_cursor()
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS change_log (
                                op_id TEXT PRIMARY KEY,
                                note_id TEXT,
                                operation_type TEXT,
                                timestamp DATETIME,
                                device_id TEXT,
                                payload TEXT,
                                lamport_clock INTEGER,
                                origin_device TEXT)""")
            self.db.commit_to_database()
        self.db_worker.execute(_op)

    def log_operation(self, note_id, operation_type, payload, lamport_timestamp, origin_device):
        def _op(connection, note_id, operation_type, payload, lamport_timestamp, origin_device):
            payload.pop("embeddings", None)

            cursor = self.db.get_database_cursor()
            op_id = str(uuid.uuid4())
            device_id = self.db.get_or_create_peer_id()

            cursor.execute("""
                    INSERT INTO change_log (op_id, note_id, operation_type, timestamp, device_id, payload, lamport_clock, origin_device)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)""",
                    (op_id, note_id, operation_type, device_id, json.dumps(payload), lamport_timestamp, origin_device))
            self.db.commit_to_database()
        self.db_worker.execute(_op, (note_id, operation_type, payload, lamport_timestamp, origin_device))

    def check_operation_exists(self, operation_id):
        def _op(connection, operation_id):
            cursor = self.db.get_database_cursor()
            cursor.execute("SELECT EXISTS (SELECT 1 FROM change_log WHERE op_id = ?) AS value_exists", (operation_id,))
            return cursor.fetchone()['value_exists']
        return self.db_worker.execute(_op, (operation_id,), wait=True)
