import uuid
import json

class ChangeLog:

    def __init__(self, db_worker, device_id):
        self.db_worker = db_worker
        self.device_id = device_id

    def create_change_log_table(self):
        def _op(connection):
            cursor = connection.cursor()
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
            connection.commit()
        self.db_worker.execute(_op)

    def log_operation(self, note_id, operation_type, payload, lamport_timestamp, origin_device):
        def _op(connection, note_id, operation_type, payload, lamport_timestamp, origin_device):
            payload.pop("embeddings", None)

            cursor = connection.cursor()
            op_id = str(uuid.uuid4())

            cursor.execute("""
                    INSERT INTO change_log (op_id, note_id, operation_type, timestamp, device_id, payload, lamport_clock, origin_device)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)""",
                    (op_id, note_id, operation_type, self.device_id, json.dumps(payload), lamport_timestamp, origin_device))
            connection.commit()
        self.db_worker.execute(_op, (note_id, operation_type, payload, lamport_timestamp, origin_device))

    def check_operation_exists(self, operation_id):
        def _op(connection, operation_id):
            cursor = connection.cursor()
            cursor.execute("SELECT EXISTS (SELECT 1 FROM change_log WHERE op_id = ?) AS value_exists", (operation_id,))
            return cursor.fetchone()['value_exists']
        return self.db_worker.execute(_op, (operation_id,), wait=True)

    def get_operations_since_timestamp(self, timestamp):
        def _op(connection, timestamp):
            cursor = connection.cursor()
            query = """
                    SELECT * FROM change_log WHERE timestamp > ? ORDER BY timestamp ASC
                    """
            cursor.execute(query, (timestamp,))
            return cursor.fetchall()
        return self.db_worker.execute(_op, args=(timestamp,), wait=True)

    def get_operation_since_lamport(self, lamport_stamp):
        def _op(connection, lamport_stamp):
            cursor = connection.cursor()
            query = "SELECT * FROM change_log WHERE lamport_clock > ? ORDER BY lamport_clock ASC"
            cursor.execute(query, (lamport_stamp,))
            return cursor.fetchall()
        return self.db_worker.execute(_op, args=(lamport_stamp,), wait=True)
