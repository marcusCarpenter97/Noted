
class NoteIndex:
    def __init__(self, db):
        self.db = db

    def create_word_index_table(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS tokens(
                        id INTEGER PRIMARY KEY,
                        note_id TEXT,
                        token TEXT,
                        count INTEGER,
                        FOREIGN KEY (note_id) REFERENCES notes (uuid))""")

    def insert_token(self, note_id, token, count, commit=True):
        cursor = self.db.get_database_cursor()
        cursor.execute("INSERT INTO tokens (note_id, token, count) VALUES(?, ?, ?)", (note_id, token, count))
        if commit:
            self.db.commit_to_database()
        return cursor.lastrowid

    def insert_many_tokens(self, rows):
        cursor = self.db.get_database_cursor()
        cursor.executemany("INSERT INTO tokens (note_id, token, count) VALUES (?, ?, ?)", rows)
        self.db.commit_to_database()

    def retrieve_tokens_for_note(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT * FROM tokens WHERE note_id = ?", (note_id,))
        return cursor.fetchall()

    def retrieve_similar_tokens(self, token):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT note_id, count FROM tokens WHERE token = ?", (token,))
        return cursor.fetchall()

    def retrieve_agerage_document_length(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT AVG(doc_len) FROM (SELECT SUM(count) AS doc_len FROM tokens GROUP BY note_id)")
        return cursor.fetchone()[0]

    def retrieve_term_frequency_in_document(self, note_id, token):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT count FROM tokens WHERE note_id = ? AND token = ?", (note_id, token))
        return cursor.fetchone()[0]

    def delete_tokens_for_note(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("DELETE FROM tokens WHERE note_id = ?", (note_id,))
        self.db.commit_to_database()

    def commit_to_database(self):
        self.db.commit_to_database()
