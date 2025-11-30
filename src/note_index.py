
class NoteIndex:
    def __init__(self, db):
        self.db = db

    def create_word_index_table(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS tokens(
                        id INTEGER PRIMARY KEY,
                        note_id INTEGER,
                        token TEXT,
                        count INTEGER,
                        FOREIGN KEY (note_id) REFERENCES notes (id))""")

    def insert_token(self, note_id, token, count):
        cursor = self.db.get_database_cursor()
        cursor.execute("INSERT INTO tokens (note_id, token, count) VALUES(?, ?, ?)", (note_id, token, count))
        self.db.commit_to_database()
        return cursor.lastrowid

    def retreive_tokens_for_note(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT * FROM tokens WHERE note_id = ?", (note_id,))
        return cursor.fetchall()

    def delete_tokens_for_note(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("DELETE FROM tokens WHERE note_id = ?", (note_id,))
        self.db.commit_to_database()
