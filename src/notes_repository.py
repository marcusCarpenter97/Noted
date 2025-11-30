
class NotesRepository:
    def __init__(self, db):
        self.db = db

    def create_notes_table(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS notes(
                        id INTEGER PRIMARY KEY,
                        title TEXT,
                        contents TEXT,
                        last_updated DATETIME,
                        embeddings BLOB,
                        tags TEXT,
                        deleted BOOLEAN DEFAULT 0)""")

    def create_note(self, title, contents, embeddings, tags):
        cursor = self.db.get_database_cursor()
        cursor.execute("INSERT INTO notes (title, contents, last_updated, embeddings, tags) VALUES(?, ?, CURRENT_TIMESTAMP, ?, ?)",
                        (title, contents, embeddings, tags))
        self.db.commit_to_database()
        return cursor.lastrowid

    def get_note(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT * FROM notes WHERE id=(?)", (note_id,))
        return cursor.fetchone()

    def list_all_notes(self, include_deleted=False):
        cursor = self.db.get_database_cursor()
        if include_deleted:
            query = "SELECT * FROM notes"
        else:
            query = "SELECT * FROM notes WHERE deleted != 1"
        cursor.execute(query)
        return cursor.fetchall()

    def update_note(self, note_id, title=None, contents=None, tags=None):
        # TODO remember to update embeddings when updating a note. This recalculation must not occur in this method.
        cursor = self.db.get_database_cursor()

        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)

        if contents is not None:
            updates.append("contents = ?")
            params.append(contents)

        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)

        if not updates:
            return None

        query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"
        params.append(note_id)

        cursor.execute(query, params)
        self.db.commit_to_database()

    def mark_note_as_deleted(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("UPDATE notes SET deleted = 1 WHERE id = ?", (note_id,))
        self.db.commit_to_database()
