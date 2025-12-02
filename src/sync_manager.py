import json
import logging 
from datetime import datetime
from database import Database
from notes_repository import NotesRepository
from remote_api_client import RemoteAPIClient

class SyncManager:

    def __init__(self, notes_repository, api_client):
        self.notes_repo = notes_repository
        self.api_client = api_client

    def get_last_sync(self, sync_file="last_sync_at.json", default_last_sync="1970-01-01T00:00:00Z"):
        try:
            with open(sync_file) as f:
                return json.load(f)
        except FileNotFoundError as e:
            logging.warning(e)
            return {"last_sync": default_last_sync}

    def sync_up(self):
        """ Send new changes to the server. """
        last_sync_at = self.get_last_sync()
        notes = self.notes_repo.get_notes_since_last_sync(last_sync_at["last_sync"])
        result = self.api_client.push_changes(notes)
        logging.info(result)

    def sync_down(self):
        """ Pull new changes from the server. """
        last_sync_at = self.get_last_sync()
        result = self.api_client.pull_changes(last_sync_at["last_sync"])
        for remote_note in result:
            local_note = self.notes_repo.get_note(remote_note['id'])

            # Create note if it does not exist.
            if local_note is None:
                # TODO Will this cause a conflict because the note has already
                # been created with an id and now it is being recreated with a
                # new id?
                local_note_id = self.notes_repo.create_note(remote_note['title'], remote_note['contents'], remote_note['embeddings'], remote_note['tags'])
                logging.info(f"Created new note from remote with id: {local_note_id}")
            else:
                remote_update_timestamp = remote_note['updated_at']
                remote_update_timestamp = datetime.strptime(remote_update_timestamp, "%Y-%m-%dT%H:%M:%SZ")  # TODO this date format might change.
                local_update_timestamp = datetime.strptime(local_note[4], "%Y-%m-%d %H:%M:%S")

                # If remote is older than local version, keep local therefore
                # there is nothing required to do. However, if remote is newer
                # than local version, keep remote.
                if remote_update_timestamp > local_update_timestamp:
                    # TODO embeddings must also be updated.
                    self.notes_repo.update_note(remote_note['id'], remote_note['title'], remote_note['contents'], remote_note['tags'])
                    logging.info(f"Succesfully updated note with id: {remote_note['id']}")

                # If the remote is marked as deleted, delete locally.
                if remote_note['deleted']:
                    # If both deleted, do nothing.
                    if local_note[7] == 0:
                        continue
                    self.notes_repo.mark_note_as_deleted(remote_note['id'])
                    logging.info(f"MArked note for deletion with id: {remote_note['id']}")

    def sync(self):
        self.sync_up()
        self.sync_down()

if __name__ == "__main__":
    db = Database()
    nr = NotesRepository(db)
    nr.create_notes_table()
    rc = RemoteAPIClient()
    sm = SyncManager(nr, rc)
    sm.sync()
