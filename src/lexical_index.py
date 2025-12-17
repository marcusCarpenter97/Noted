
class LexicalIndex:

    def __init__(self, db):
        self.db = db

    def create_lexical_table(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS lexical USING fts5(note_id, title, contents)")

    def index_note_for_lexical_search(self, note_id, title, contents):
        cursor = self.db.get_database_cursor()
        cursor.execute("DELETE FROM lexical WHERE note_id = ?", (note_id,))
        cursor.execute("INSERT INTO lexical (note_id, title, contents) VALUES (?, ?, ?)", (note_id, title, contents))
        self.db.commit_to_database()

    def delete_note_from_lexical_search(self, note_id):
        cursor = self.db.get_database_cursor()
        cursor.execute("DELETE FROM lexical WHERE note_id = ?", (note_id,))
        self.db.commit_to_database()

    def get_note_from_lexical_index(self, note_id):
        cursor = self.db.get_database_cursor()
        result = cursor.execute("SELECT * FROM lexical WHERE note_id = ?", (note_id,))
        return result.fetchone()

    def search_lexical_index(self, query):
        cursor = self.db.get_database_cursor()
        results = cursor.execute("SELECT note_id FROM lexical WHERE lexical = ?", (query,))
        return results.fetchall()
