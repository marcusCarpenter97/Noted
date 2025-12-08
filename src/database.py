import logging 
import sqlite3
import numpy as np

DATABASE_PATH = 'database/database.db'

class Database:
    "Implements a database connection to SQLite as a singleton."

    _instance = None
    _initialized = None

    def __new__(cls, database_name=DATABASE_PATH):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            return cls._instance

        if database_name != cls._instance.name:
            logging.warning(f"Warning: Database already initialized with {cls._instance.name}, ignoring new name {database_name}.")
        return cls._instance

    def __init__(self, database_name=DATABASE_PATH):
        if self._initialized:
            return

        self.name = database_name
        self.connection = sqlite3.connect(database_name)
        self.connection.row_factory = sqlite3.Row
        self._initialized = True

    def get_database_cursor(self):
        return self.connection.cursor()

    def commit_to_database(self):
        self.connection.commit()

    def close_database_connection(self):
        self.connection.close()

    def get_or_create_peer_id(self):
        cursor = self.get_database_cursor()
        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS settings(
                            key TEXT PRIMARY KEY,
                            value TEXT)""")
        cursor.execute("SELECT value FROM settings WHERE key='peer_id'")
        row = cursor.fetchone()

        if row:
            return row[0]

        peer_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("peer_id", peer_id))
        self.commit_to_database()

        return peer_id
