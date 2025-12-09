import json
import logging
from datetime import datetime
from database import Database
from change_log_repository import ChangeLog
from notes_repository import NotesRepository
from remote_api_client import RemoteAPIClient

class SyncManager:

    def __init__(self, db, notes_repository, api_client):
        self.db = db
        self.notes_repo = notes_repository
        self.api_client = api_client
        self.create_last_sync_table()
        self.initialize_sync_table()

    def create_last_sync_table(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS last_sync (
                            id INTEGER PRIMARY KEY CHECK (id = 1) DEFAULT 1,
                            last_updated DATETIME)""")

    def initialize_sync_table(self):
        # Insert if empty.
        cursor = self.db.get_database_cursor()
        cursor.execute("""INSERT INTO last_sync (last_updated) SELECT CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT * FROM last_sync)""")
        self.db.commit_to_database()

    def update_last_sync(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("UPDATE last_sync SET last_updated = CURRENT_TIMESTAMP WHERE id = 1")
        self.db.commit_to_database()

    def get_last_sync(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("SELECT last_updated FROM last_sync WHERE id = 1")
        return cursor.fetchone()[0]

    def sync_up(self, batch_size=50):
        """ Send new changes to the server. """
        last_sync_at = self.get_last_sync()
        operations = self.notes_repo.get_operations_since(last_sync_at)

        try:
            for i in range(0, len(operations), batch_size):
                batch = operations[i : i + batch_size]
                result = self.api_client.push_changes(batch)
        except Exception as e:
            logging.error(f"Failed to push changes: %s", e)
            return

        logging.info(result)

    def sync_down(self):
        """ Pull new changes from the server. """
        last_sync_at = self.get_last_sync()

        try:  # TODO add batching to pull_changes function
            result = self.api_client.pull_changes(last_sync_at)
        except Exception as e:
            logging.error(f"Failed to pull changes: %s", e)
            return

        for remote_operation in result:
            local_note = self.notes_repo.get_note(remote_operation['uuid'])

            if remote_operation['operation_type'] == 'create':
                if local_note is None:
                    self.notes_repo.insert_note(remote_operation['uuid'], remote_operation['payload']['title'],
                                                remote_operation['payload']['contents'], remote_operation['payload']['created_at'],
                                                remote_operation['payload']['last_updated'],
                                                remote_operation['payload']['embeddings'], remote_operation['payload']['tags'])
                    logging.info(f"Inserted note from remote with id: {remote_operation['uuid']}")
                    self.update_last_sync()
                else:
                    logging.warning(f"Could not create note because a note with this id already exists. Note id : {remote_operation['uuid']}")

            if remote_operation['operation_type'] == 'update':
                if local_note is not None:  # Use .get bacause parameters may not exist in update function.
                    self.notes_repo.update_note(remote_operation['uuid'],
                                                remote_operation['payload'].get('title', None), remote_operation['payload'].get('contents', None),
                                                remote_operation['payload'].get('embeddings', None),
                                                remote_operation['payload'].get('tags', None))
                    logging.info(f"Succesfully updated note with id: {remote_operation['uuid']}")
                    self.update_last_sync()
                else:
                    logging.warning(f"Could not update note becuase a note with this id does not exist. Note id : {remote_operation['uuid']}")

            if remote_operation['operation_type'] == 'delete':
                if local_note is not None:
                    self.notes_repo.mark_note_as_deleted(remote_operation['uuid'])
                    logging.info(f"Marked note for deletion with id: {remote_operation['uuid']}")
                    self.update_last_sync()
                else:
                    logging.warning(f"Could not delete note becuase a note with this id does not exist. Note id : {remote_operation['uuid']}")

    def sync(self):
        self.sync_up()
        self.sync_down()

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ]
    )

    db = Database()
    cl = ChangeLog(db)
    cl.create_change_log_table()
    nr = NotesRepository(db)
    nr.create_notes_table()
    rc = RemoteAPIClient()
    sm = SyncManager(db, nr, rc)
    sm.sync()
