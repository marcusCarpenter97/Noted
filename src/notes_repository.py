import uuid

class NotesRepository:
    def __init__(self, db, li):
        self.db = db
        self.lexical_index = li

    def create_notes_table(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS notes(
                        uuid TEXT PRIMARY KEY,
                        title TEXT,
                        contents TEXT,
                        created_at DATETIME,
                        last_updated DATETIME,
                        embeddings BLOB,
                        tags TEXT,
                        deleted BOOLEAN DEFAULT 0)""")

    def create_note(self, title, contents, embeddings, tags):
        cursor = self.db.get_database_cursor()
        unique_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO notes (uuid, title, contents, created_at, last_updated, embeddings, tags) VALUES(?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?)", (unique_id, title, contents, embeddings, tags))
        self.db.commit_to_database()
        self.lexical_index.index_note_for_lexical_search(uuid, title, contents)
        return unique_id

    def insert_note(self, uuid, title, contents, created_at, last_updated, embeddings, tags):
        cursor = self.db.get_database_cursor()
        cursor.execute("INSERT INTO notes (uuid, title, contents, created_at, last_updated, embeddings, tags) VALUES(?, ?, ?, ?, ?, ?, ?)", (uuid, title, contents, created_at, last_updated, embeddings, tags))
        self.db.commit_to_database()

    def get_note(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT * FROM notes WHERE uuid=(?)", (note_id,))
        return cursor.fetchone()

    def list_all_notes(self, include_deleted=False):
        cursor = self.db.get_database_cursor()
        if include_deleted:
            query = "SELECT * FROM notes"
        else:
            query = "SELECT * FROM notes WHERE deleted != 1"
        cursor.execute(query)
        return cursor.fetchall()

    def update_note(self, note_id, title=None, contents=None, embeddings=None, tags=None):
        cursor = self.db.get_database_cursor()

        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)

        if contents is not None:
            updates.append("contents = ?")
            params.append(contents)

        if embeddings is not None:
            updates.append("embeddings = ?")
            params.append(embeddings)

        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)

        updates.append("last_updated = CURRENT_TIMESTAMP")

        if not params and len(updates) == 1:
            return None

        query = f"UPDATE notes SET {', '.join(updates)} WHERE uuid = ?"
        params.append(note_id)

        cursor.execute(query, params)
        self.db.commit_to_database()

    def get_notes_since_last_sync(self, last_sync):
        # Get all notes whose last_updated is more recent than last_sync.
        cursor = self.db.get_database_cursor()
        query = "SELECT * FROM notes WHERE last_updated > ?"
        cursor.execute(query, (last_sync,))
        return cursor.fetchall()

    def mark_note_as_deleted(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("UPDATE notes SET deleted = 1 WHERE uuid = ?", (note_id,))
        self.db.commit_to_database()
