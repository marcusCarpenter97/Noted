
class LexicalIndex:

    def __init__(self, db_worker):
        self.db_worker = db_worker

    def create_lexical_table(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS lexical USING fts5(note_id, title, contents)")
        self.db_worker.execute(_op)

    def index_note_for_lexical_search(self, note_id, title, contents):
        def _op(connection, note_id, title, contents):
            cursor = connection.cursor()
            cursor.execute("DELETE FROM lexical WHERE note_id = ?", (note_id,))
            cursor.execute("INSERT INTO lexical (note_id, title, contents) VALUES (?, ?, ?)", (note_id, title, contents))
            connection.commit()
        self.db_worker.execute(_op, (note_id, title, contents))

    def delete_note_from_lexical_search(self, note_id):
        def _op(connection, note_id):
            cursor = connection.cursor()
            cursor.execute("DELETE FROM lexical WHERE note_id = ?", (note_id,))
            connection.commit()
        self.db_worker.execute(_op, (note_id,))

    def get_note_from_lexical_index(self, note_id):
        def _op(connection, note_id):
            cursor = connection.cursor()
            result = cursor.execute("SELECT * FROM lexical WHERE note_id = ?", (note_id,))
            return result.fetchone()
        return self.db_worker.execute(_op, (note_id,), wait=True)

    def search_lexical_index(self, query):
        def _op(connection, query):
            cursor = connection.cursor()
            results = cursor.execute("SELECT note_id FROM lexical WHERE lexical = ?", (query,))
            return results.fetchall()
        return self.db_worker.execute(_op, (query,), wait=True)
