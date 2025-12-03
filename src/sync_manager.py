import json
import logging
from datetime import datetime
from database import Database
from notes_repository import NotesRepository
from remote_api_client import RemoteAPIClient

class SyncManager:

    sync_file = "last_sync_at.json"

    def __init__(self, notes_repository, api_client):
        self.notes_repo = notes_repository
        self.api_client = api_client

    def update_last_sync(self):
        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        d = {"last_sync": current_timestamp}
        with open(self.sync_file, 'w') as f:
            json.dump(d, f)

    def get_last_sync(self, sync_file=sync_file, default_last_sync="1970-01-01 00:00:00"):
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

        try:
            result = self.api_client.push_changes(notes)
        except Exception as e:
            logging.error(f"Failed to push changes: %s", e)
            return

        logging.info(result)

    def sync_down(self):
        """ Pull new changes from the server. """
        last_sync_at = self.get_last_sync()

        try:
            result = self.api_client.pull_changes(last_sync_at["last_sync"])
        except Exception as e:
            logging.error(f"Failed to pull changes: %s", e)
            return

        for remote_note in result:
            local_note = self.notes_repo.get_note(remote_note['uuid'])

            # Create note if it does not exist.
            if local_note is None:
                self.notes_repo.insert_note(remote_note['uuid'], remote_note['title'],
                                            remote_note['contents'], remote_note['created_at'],
                                            remote_note['last_updated'], remote_note['embeddings'], remote_note['tags'])
                logging.info(f"Inserted note from remote with id: {remote_note['uuid']}")
                self.update_last_sync()
            else:
                remote_update_timestamp = remote_note['last_updated']
                remote_update_timestamp = datetime.strptime(remote_update_timestamp, "%Y-%m-%d %H:%M:%S")
                local_update_timestamp = datetime.strptime(local_note['last_updated'], "%Y-%m-%d %H:%M:%S")

                # If remote is older than local version, keep local therefore
                # there is nothing required to do. However, if remote is newer
                # than local version, keep remote.
                if remote_update_timestamp > local_update_timestamp:
                    self.notes_repo.update_note(remote_note['uuid'],
                                                remote_note['title'], remote_note['contents'], remote_note['embeddings'],
                                                remote_note['tags'])
                    logging.info(f"Succesfully updated note with id: {remote_note['uuid']}")
                    self.update_last_sync()

                    # If the remote is marked as deleted, delete locally.
                    if remote_note['deleted']:
                        # If both deleted, do nothing.
                        if local_note['deleted'] == 1:
                            continue
                        self.notes_repo.mark_note_as_deleted(remote_note['uuid'])
                        logging.info(f"Marked note for deletion with id: {remote_note['uuid']}")
                        self.update_last_sync()

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
    nr = NotesRepository(db)
    nr.create_notes_table()
    rc = RemoteAPIClient()
    sm = SyncManager(nr, rc)
    sm.sync()
