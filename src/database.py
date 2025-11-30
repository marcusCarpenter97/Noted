import logging 
import sqlite3
import numpy as np

DATABASE_NAME = 'database.db'

class Database:
    "Implements a database connection to SQLite as a singleton."

    _instance = None
    _initialized = None

    def __new__(cls, database_name=DATABASE_NAME):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            return cls._instance

        if database_name != cls._instance.name:
            logging.warning(f"Warning: Database already initialized with {cls._instance.name}, ignoring new name {database_name}.")
        return cls._instance

    def __init__(self, database_name=DATABASE_NAME):
        if self._initialized:
            return

        self.name = database_name
        self.connection = sqlite3.connect(database_name)
        self._initialized = True

    def get_database_cursor(self):
        return self.connection.cursor()

    def create_notes_table(self):
        cursor = self.get_database_cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS notes(
                        id INTEGER PRIMARY KEY,
                        title TEXT,
                        contents TEXT,
                        last_updated DATETIME,
                        embeddings BLOB,
                        tags TEXT,
                        deleted BOOLEAN DEFAULT 0)""")

    def create_note(self, title, contents, embeddings, tags):
        cursor = self.get_database_cursor()
        cursor.execute("INSERT INTO notes (title, contents, last_updated, embeddings, tags) VALUES(?, ?, CURRENT_TIMESTAMP, ?, ?)",
                        (title, contents, embeddings, tags))
        self.commit_to_database()
        return cursor.lastrowid

    def get_note(self, note_id):
        cursor = self.get_database_cursor()
        cursor.execute("SELECT * FROM notes WHERE id=(?)", (note_id,))
        return cursor.fetchone()

    def list_all_notes(self, include_deleted=False):
        cursor = self.get_database_cursor()
        if include_deleted:
            query = "SELECT * FROM notes"
        else:
            query = "SELECT * FROM notes WHERE deleted != 1"
        cursor.execute(query)
        return cursor.fetchall()

    def update_note(self, note_id, title=None, contents=None, tags=None):
        # TODO remember to update embeddings when updating a note. This recalculation must not occur in this method.
        cursor = self.get_database_cursor()

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
        self.commit_to_database()

    def mark_note_as_deleted(self, note_id):
        cursor = self.get_database_cursor()
        cursor.execute("UPDATE notes SET deleted = 1 WHERE id = ?", (note_id,))
        self.commit_to_database()

    def commit_to_database(self):
        self.connection.commit()

    def close_database_connection(self):
        self.connection.close()

