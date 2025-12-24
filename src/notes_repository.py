import uuid
from hashing import compute_note_hash

class NotesRepository:
    def __init__(self, db_worker):
        self.db_worker = db_worker

    def create_notes_table(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS notes(
                            uuid TEXT PRIMARY KEY,
                            title TEXT,
                            contents TEXT,
                            created_at DATETIME,
                            last_updated DATETIME,
                            embeddings BLOB,
                            tags TEXT,
                            deleted BOOLEAN DEFAULT 0,
                            note_hash TEXT)""")
        self.db_worker.execute(_op)

    def create_note(self, title, contents, embeddings, tags):
        def _op(connection, title, contents, embeddings, tags):
            cursor = connection.cursor()
            unique_id = str(uuid.uuid4())
            note_hash = compute_note_hash(title, contents, tags, embeddings, deleted=0)
            cursor.execute("INSERT INTO notes (uuid, title, contents, created_at, last_updated, embeddings, tags, note_hash) VALUES(?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?)", (unique_id, title, contents, embeddings, tags, note_hash))
            connection.commit()
            return unique_id
        return self.db_worker.execute(_op, args=(title, contents, embeddings, tags), wait=True)

    def insert_note(self, uuid, title, contents, created_at, last_updated, embeddings, tags):
        def _op(connection, uuid, title, contents, created_at, last_updated, embeddings, tags):
            cursor = connection.cursor()
            note_hash = compute_note_hash(title, contents, tags, embeddings, deleted=0)
            cursor.execute("INSERT INTO notes (uuid, title, contents, created_at, last_updated, embeddings, tags, note_hash) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", (uuid, title, contents, created_at, last_updated, embeddings, tags, note_hash))
            connection.commit()
        self.db_worker.execute(_op)

    def get_note(self, note_id):
        def _op(connection, note_id):
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM notes WHERE uuid=(?)", (note_id,))
            return cursor.fetchone()
        return self.db_worker.execute(_op, args=(note_id,), wait=True)

    def get_number_of_non_deleted_notes(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM notes WHERE deleted = 0")
            return cursor.fetchone()[0]
        return self.db_worker.execute(_op, wait=True)

    def list_all_notes(self, include_deleted=False):
        def _op(connection, include_deleted):
            cursor = connection.cursor()
            if include_deleted:
                query = "SELECT * FROM notes"
            else:
                query = "SELECT * FROM notes WHERE deleted != 1"
            cursor.execute(query)
            return cursor.fetchall()
        return self.db_worker.execute(_op, args=(include_deleted,), wait=True)

    def update_note(self, note_id, title=None, contents=None, embeddings=None, tags=None):
        def _op(connection, note_id, title, contents, embeddings, tags):
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM notes WHERE uuid = ?", (note_id,))
            current_note = cursor.fetchone()

            if current_note is None:
                return None

            _, cur_title, cur_contents, _, _, cur_embeddings, cur_tags, cur_deleted, _, = current_note

            new_title = title if title is not None else cur_title
            new_contents = contents if contents is not None else cur_contents
            new_embeddings = embeddings if embeddings is not None else cur_embeddings
            new_tags = tags if tags is not None else cur_tags

            new_hash = compute_note_hash(new_title, new_contents, new_tags, new_embeddings, cur_deleted)

            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(new_title)

            if contents is not None:
                updates.append("contents = ?")
                params.append(new_contents)

            if embeddings is not None:
                updates.append("embeddings = ?")
                params.append(new_embeddings)

            if tags is not None:
                updates.append("tags = ?")
                params.append(new_tags)

            updates.append("last_updated = CURRENT_TIMESTAMP")

            if not params and len(updates) == 1:
                return None

            query = f"UPDATE notes SET {', '.join(updates)} WHERE uuid = ?"
            params.append(note_id)

            cursor.execute(query, params)
            connection.commit()
        return self.db_worker.execute(_op, args=(note_id, title, contents, embeddings, tags), wait=True)

    def get_operations_since(self, timestamp):
        def _op(connection, timestamp):
            cursor = connection.cursor()
            query = """
                    SELECT * FROM change_log WHERE timestamp > ? ORDER BY timestamp ASC
                    """
            cursor.execute(query, (timestamp,))
            return cursor.fetchall()
        self.db_worker.execute(_op, args=(timestamp,), wait=True)

    def mark_note_as_deleted(self, note_id):
        def _op(connection, note_id):
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM notes WHERE uuid = ?", (note_id,))
            current_note = cursor.fetchone()

            if current_note is None:
                return None

            _, title, contents, _, _, embeddings, tags, _, _ = current_note

            new_hash = compute_note_hash(title, contents, tags, embeddings, deleted=1)
            cursor.execute("UPDATE notes SET deleted = 1, note_hash = ?, last_updated = CURRENT_TIMESTAMP WHERE uuid = ?", (new_hash, note_id))
            connection.commit()
        return self.db_worker.execute(_op, args=(note_id,), wait=True)
