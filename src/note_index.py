
class NoteIndex:
    def __init__(self, db_worker):
        self.db_worker = db_worker

    def create_word_index_table(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS tokens(
                            id INTEGER PRIMARY KEY,
                            note_id TEXT,
                            token TEXT,
                            count INTEGER,
                            FOREIGN KEY (note_id) REFERENCES notes (uuid))""")
        self.db_worker.execute(_op)

    def insert_token(self, note_id, token, count, commit=True):
        def _op(connection, note_id, token, count, commit):
            cursor = connection.cursor()
            cursor.execute("INSERT INTO tokens (note_id, token, count) VALUES(?, ?, ?)", (note_id, token, count))
            if commit:
                connection.commit()
            return cursor.lastrowid
        return self.db_worker.execute(_op, (note_id, token, count, commit), wait=True)

    def insert_many_tokens(self, rows):
        def _op(connection, rows):
            cursor = connection.cursor()
            cursor.executemany("INSERT INTO tokens (note_id, token, count) VALUES (?, ?, ?)", rows)
            connection.commit()
        self.db_worker.execute(_op, args=(rows,), wait=True)

    def retrieve_tokens_for_note(self, note_id):
        def _op(connection, note_id):
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM tokens WHERE note_id = ?", (note_id,))
            return cursor.fetchall()
        return self.db_worker.execute(_op, (note_id,), wait=True)

    def retrieve_similar_tokens(self, token):
        def _op(connection, token):
            cursor = connection.cursor()
            cursor.execute("SELECT note_id, count FROM tokens WHERE token = ?", (token,))
            return cursor.fetchall()
        return self.db_worker.execute(_op, (token,), wait=True)

    def retrieve_agerage_document_length(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("SELECT AVG(doc_len) FROM (SELECT SUM(count) AS doc_len FROM tokens GROUP BY note_id)")
            return cursor.fetchone()[0]
        return self.db_worker.execute(_op, wait=True)

    def retrieve_term_frequency_in_document(self, note_id, token):
        def _op(connection, note_id, token):
            cursor = connection.cursor()
            cursor.execute("SELECT count FROM tokens WHERE note_id = ? AND token = ?", (note_id, token))
            return cursor.fetchone()[0]
        return self.db_worker.execute(_op, (note_id, token), wait=True)

    def delete_tokens_for_note(self, note_id):
        def _op(connection, note_id):
            cursor = connection.cursor()
            cursor.execute("DELETE FROM tokens WHERE note_id = ?", (note_id,))
            connection.commit()
        return self.db_worker.execute(_op, (note_id,), wait=True)

    def commit_to_database(self):  # TODO revise this. Where is it called?
        connection.commit()
